package com.setu.remote;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

public class MainActivity extends Activity {
    private static final int GREEN = Color.rgb(49,94,72), INK = Color.rgb(37,58,48);
    private final ExecutorService actions = Executors.newSingleThreadExecutor();
    private ScheduledExecutorService frames;
    private final AtomicInteger generation = new AtomicInteger();
    private volatile String token, baseUrl;
    private LinearLayout root;
    private ImageView screen;
    private TextView state;
    private EditText address, password;
    private float downX, downY;
    private long downAt;
    private boolean connecting;

    @Override public void onCreate(Bundle b) { super.onCreate(b); getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE); showConnect(); }
    private int dp(int n) { return (int)(n * getResources().getDisplayMetrics().density + .5f); }
    private TextView text(String value, int size, int color) { TextView t = new TextView(this); t.setText(value); t.setTextSize(size); t.setTextColor(color); return t; }
    private Button button(String value) { Button b = new Button(this); b.setText(value); b.setAllCaps(false); b.setTextColor(Color.WHITE); b.setBackgroundTintList(android.content.res.ColorStateList.valueOf(GREEN)); return b; }
    private void setupRoot() {
        root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(dp(20),dp(24),dp(20),dp(16)); root.setBackgroundColor(Color.rgb(247,248,244)); setContentView(root);
        TextView logo = text("setu.", 27, GREEN); logo.setTypeface(null, Typeface.BOLD); root.addView(logo);
    }
    private void showConnect() {
        setupRoot();
        ScrollView scroll = new ScrollView(this); root.addView(scroll);
        LinearLayout form = new LinearLayout(this); form.setOrientation(LinearLayout.VERTICAL); scroll.addView(form);
        TextView title = text("Your PC, within reach.", 28, INK); title.setPadding(0,dp(30),0,dp(10)); form.addView(title);
        TextView note = text("Connect Tailscale on your PC and phone first. Start sharing in Setu PC Host, then enter the address and key shown there.", 15, Color.rgb(112,130,115)); note.setLineSpacing(dp(3),1); form.addView(note);
        TextView al = text("TAILSCALE ADDRESS", 11, GREEN); al.setPadding(0,dp(28),0,dp(4)); form.addView(al);
        address = new EditText(this); address.setSingleLine(); address.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI); address.setHint("100.x.x.x:8000"); form.addView(address);
        TextView kl = text("ACCESS KEY", 11, GREEN); kl.setPadding(0,dp(20),0,dp(4)); form.addView(kl);
        password = new EditText(this); password.setSingleLine(); password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD); password.setHint("Key from your PC"); form.addView(password);
        Button connect = button("Connect to PC  →"); LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(-1, dp(52)); bp.topMargin = dp(25); form.addView(connect, bp);
        state = text("Never share your key. Only connect to your own PC.", 12, Color.rgb(112,130,115)); state.setPadding(0,dp(20),0,0); form.addView(state);
        connect.setOnClickListener(v -> {
            if (connecting) return;
            String addr = address.getText().toString().trim(); String key = password.getText().toString();
            if (!validAddress(addr)) { state.setText("Enter a Tailscale IPv4 address and port, for example 100.101.102.103:8000."); return; }
            if (key.isEmpty()) { state.setText("Enter the access key shown on your PC."); return; }
            connecting = true; connect.setEnabled(false); state.setText("Connecting…"); final int g = generation.incrementAndGet(); final String url = "http://" + addr;
            actions.execute(() -> {
                try {
                    JSONObject data = new JSONObject(); data.put("password", key);
                    JSONObject result = new JSONObject(new String(request(url, "/api/login", "POST", null, data.toString()), StandardCharsets.UTF_8));
                    String newToken = result.getString("token");
                    runOnUiThread(() -> { if (generation.get() != g || isFinishing()) { logout(url, newToken); return; } connecting = false; baseUrl = url; token = newToken; showSession(); startFrames(g); });
                } catch (Exception e) { runOnUiThread(() -> { if (generation.get() != g || isFinishing()) return; connecting = false; connect.setEnabled(true); state.setText("Could not connect. Check Tailscale, address and access key. " + e.getMessage()); }); }
            });
        });
    }
    static boolean validAddress(String input) {
        if (!input.matches("100\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}:\\d{1,5}")) return false;
        String[] parts = input.split("[:.]");
        try { int b = Integer.parseInt(parts[1]), c = Integer.parseInt(parts[2]), d = Integer.parseInt(parts[3]), port = Integer.parseInt(parts[4]); return b >= 64 && b <= 127 && c <= 255 && d <= 255 && port >= 1 && port <= 65535; } catch (Exception e) { return false; }
    }
    private void showSession() {
        setupRoot();
        state = text("LIVE SESSION  •  Tap to click · Hold for right click · Swipe to scroll", 12, GREEN); state.setPadding(0,dp(20),0,dp(12)); root.addView(state);
        screen = new ImageView(this); screen.setBackgroundColor(Color.rgb(36,54,43)); screen.setScaleType(ImageView.ScaleType.FIT_CENTER); screen.setAdjustViewBounds(false);
        root.addView(screen, new LinearLayout.LayoutParams(-1, 0, 1));
        screen.setOnTouchListener((v, event) -> {
            if (event.getAction() == MotionEvent.ACTION_DOWN) { downX = event.getX(); downY = event.getY(); downAt = System.currentTimeMillis(); return true; }
            if (event.getAction() == MotionEvent.ACTION_UP) {
                float dy = event.getY() - downY;
                if (Math.abs(dy) > dp(30)) { send("scroll", 0, 0, null, null, null, dy > 0 ? 3 : -3); return true; }
                Drawable drawable = screen.getDrawable(); if (drawable == null) return true;
                float scale = Math.min((float)screen.getWidth()/drawable.getIntrinsicWidth(), (float)screen.getHeight()/drawable.getIntrinsicHeight());
                float width = drawable.getIntrinsicWidth()*scale, height = drawable.getIntrinsicHeight()*scale;
                float x = (event.getX()-(screen.getWidth()-width)/2)/width, y = (event.getY()-(screen.getHeight()-height)/2)/height;
                if (x >= 0 && x <= 1 && y >= 0 && y <= 1) send("click", x, y, System.currentTimeMillis()-downAt > 600 ? "right" : "left", null, null, 0);
                return true;
            } return true;
        });
        LinearLayout row = new LinearLayout(this); row.setGravity(Gravity.CENTER); row.setPadding(0,dp(12),0,0); root.addView(row);
        Button keyboard = button("Keyboard"); Button keys = button("Keys"); Button disconnect = button("Disconnect");
        row.addView(keyboard, new LinearLayout.LayoutParams(0, dp(48), 1)); row.addView(keys, new LinearLayout.LayoutParams(0, dp(48), 1)); row.addView(disconnect, new LinearLayout.LayoutParams(0, dp(48), 1));
        keyboard.setOnClickListener(v -> { EditText input = new EditText(this); input.setHint("ASCII text"); new AlertDialog.Builder(this).setTitle("Send text to PC").setView(input).setNegativeButton("Cancel", null).setPositiveButton("Send", (d,w) -> send("text",0,0,null,input.getText().toString(),null,0)).show(); });
        keys.setOnClickListener(v -> { String[] options = {"enter","backspace","tab","esc","space","up","down","left","right","delete","home","end"}; new AlertDialog.Builder(this).setTitle("Send a key").setItems(options, (d,which) -> send("key",0,0,null,null,options[which],0)).show(); });
        disconnect.setOnClickListener(v -> { disconnect(); showConnect(); });
    }
    private void startFrames(int g) {
        frames = Executors.newSingleThreadScheduledExecutor();
        frames.scheduleWithFixedDelay(() -> {
            String t = token, url = baseUrl; if (t == null || g != generation.get()) return;
            try {
                byte[] data = request(url, "/api/screen", "GET", t, null); Bitmap bitmap = BitmapFactory.decodeByteArray(data, 0, data.length);
                if (bitmap == null) throw new Exception("Invalid screen image");
                runOnUiThread(() -> { if (g == generation.get() && screen != null) screen.setImageBitmap(bitmap); });
            } catch (Exception e) { runOnUiThread(() -> { if (g == generation.get()) { disconnect(); showConnect(); state.setText("Session ended or screen unavailable. Check PC host and Tailscale."); } }); }
        }, 0, 900, TimeUnit.MILLISECONDS);
    }
    private void send(String type, float x, float y, String button, String text, String key, int amount) {
        final String t = token, url = baseUrl; final int g = generation.get(); if (t == null) return;
        actions.execute(() -> { try { JSONObject json = new JSONObject(); json.put("type", type); json.put("x", x); json.put("y", y); if (button != null) json.put("button", button); if (text != null) json.put("text", text); if (key != null) json.put("key", key); json.put("amount", amount); request(url,"/api/input","POST",t,json.toString()); } catch(Exception e) { runOnUiThread(() -> { if (g == generation.get()) Toast.makeText(this, "Input failed: " + e.getMessage(), Toast.LENGTH_SHORT).show(); }); } });
    }
    private byte[] request(String url, String path, String method, String auth, String json) throws Exception {
        HttpURLConnection c = (HttpURLConnection)new URL(url + path).openConnection();
        c.setConnectTimeout(7000); c.setReadTimeout(10000); c.setInstanceFollowRedirects(false); c.setRequestMethod(method); c.setUseCaches(false);
        if (auth != null) c.setRequestProperty("Authorization", "Bearer " + auth);
        try {
            if (json != null) { c.setDoOutput(true); c.setRequestProperty("Content-Type", "application/json"); try (OutputStream out = c.getOutputStream()) { out.write(json.getBytes(StandardCharsets.UTF_8)); } }
            int code = c.getResponseCode(); if (code < 200 || code >= 300) throw new Exception("Server returned " + code);
            try (InputStream in = c.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) { byte[] buf = new byte[8192]; int n, total = 0; while ((n = in.read(buf)) != -1) { total += n; if (total > 8*1024*1024) throw new Exception("Response too large"); out.write(buf,0,n); } return out.toByteArray(); }
        } finally { c.disconnect(); }
    }
    private void logout(String url, String t) { actions.execute(() -> { try { request(url,"/api/logout","POST",t,null); } catch(Exception ignored) {} }); }
    private void disconnect() { generation.incrementAndGet(); connecting = false; if (frames != null) { frames.shutdownNow(); frames = null; } String t = token, url = baseUrl; token = null; baseUrl = null; if (t != null && url != null) logout(url,t); }
    @Override protected void onStop() { super.onStop(); if (token != null || connecting) { disconnect(); showConnect(); } }
    @Override protected void onDestroy() { disconnect(); actions.shutdown(); super.onDestroy(); }
}
