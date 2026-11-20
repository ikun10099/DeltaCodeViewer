package cn.deltacode.loadout;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.zip.GZIPInputStream;

public class MainActivity extends Activity {

    private static final String HOST = "delta-code.cn";
    private static final String API_PATH = "/api/loadouts";
    private static final String DAILY_PATH = "/api/daily-password";
    private static final String UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)";
    private static final String CACHE_NAME = "cache.json";
    private static final String DAILY_NAME = "daily.json";

    private WebView web;
    private volatile boolean fetching = false;
    private volatile boolean dailyFetching = false;

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Window w = getWindow();
        w.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        w.setStatusBarColor(Color.parseColor("#0e131b"));
        w.setNavigationBarColor(Color.parseColor("#080b10"));

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#080b10"));

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setLoadWithOverviewMode(false);
        s.setUseWideViewPort(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setTextZoom(100);
        s.setCacheMode(WebSettings.LOAD_NO_CACHE);
        if (Build.VERSION.SDK_INT >= 21) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        }

        web.setWebViewClient(new WebViewClient());
        web.setWebChromeClient(new WebChromeClient());
        web.addJavascriptInterface(new Bridge(), "Native");

        setContentView(web);
        web.loadUrl("file:///android_asset/index.html");
    }

    /** JS -> Java 桥。所有方法在 JavaBridge 线程执行，不阻塞 UI。 */
    public class Bridge {

        @JavascriptInterface
        public String loadCache() {
            return readFile(CACHE_NAME);
        }

        private String readFile(String name) {
            try {
                File f = new File(getFilesDir(), name);
                if (!f.exists()) return "";
                java.io.FileInputStream in = new java.io.FileInputStream(f);
                ByteArrayOutputStream bo = new ByteArrayOutputStream();
                byte[] buf = new byte[8192];
                int n;
                while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
                in.close();
                return new String(bo.toByteArray(), "UTF-8");
            } catch (Throwable t) {
                return "";
            }
        }

        @JavascriptInterface
        public String readPref(String key, String def) {
            SharedPreferences sp = getSharedPreferences("app", MODE_PRIVATE);
            return sp.getString(key, def);
        }

        @JavascriptInterface
        public void writePref(String key, String value) {
            SharedPreferences sp = getSharedPreferences("app", MODE_PRIVATE);
            sp.edit().putString(key, value).apply();
        }

        @JavascriptInterface
        public void startFetch() {
            if (fetching) return;
            fetching = true;
            new Thread(new Runnable() {
                public void run() {
                    doFetch();
                }
            }).start();
        }

        @JavascriptInterface
        public boolean isFetching() {
            return fetching;
        }

        /** 今日地图密码：读缓存，没有返回空串。 */
        @JavascriptInterface
        public String loadDaily() {
            return readFile(DAILY_NAME);
        }

        /** 今日地图密码：后台拉取，完成后回调 window.__native.onDaily(json) / onDailyError(msg)。 */
        @JavascriptInterface
        public void startDailyFetch() {
            if (dailyFetching) return;
            dailyFetching = true;
            new Thread(new Runnable() {
                public void run() {
                    doDailyFetch();
                }
            }).start();
        }

        @JavascriptInterface
        public boolean isDailyFetching() {
            return dailyFetching;
        }

        @JavascriptInterface
        public void copy(String text) {
            try {
                ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                cm.setPrimaryClip(ClipData.newPlainText("loadout", text == null ? "" : text));
            } catch (Throwable ignored) {
            }
        }

        @JavascriptInterface
        public void toast(final String msg) {
            runOnUiThread(new Runnable() {
                public void run() {
                    Toast.makeText(MainActivity.this, msg, Toast.LENGTH_SHORT).show();
                }
            });
        }

        @JavascriptInterface
        public String appVersion() {
            try {
                return getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
            } catch (Throwable t) {
                return "3.0";
            }
        }
    }

    private void emit(String fn, String jsonArgs) {
        final String js = "window.__native && window.__native." + fn + "(" + jsonArgs + ");";
        runOnUiThread(new Runnable() {
            public void run() {
                try {
                    if (Build.VERSION.SDK_INT >= 19) {
                        web.evaluateJavascript(js, null);
                    } else {
                        web.loadUrl("javascript:" + js);
                    }
                } catch (Throwable ignored) {
                }
            }
        });
    }

    private void doFetch() {
        List<String> failed = new ArrayList<String>();
        JSONArray items = new JSONArray();
        int pages = 1, total = 0;
        try {
            JSONObject first = fetchPage(1);
            JSONArray a1 = first.optJSONArray("loadouts");
            if (a1 == null) throw new Exception("响应缺少 loadouts 字段");
            for (int i = 0; i < a1.length(); i++) items.put(a1.getJSONObject(i));
            pages = first.optInt("totalPages", 1);
            if (pages < 1) pages = 1;
            total = first.optInt("total", items.length());
            emit("onProgress", pages + "," + 1 + "," + total + "," + items.length());
            for (int p = 2; p <= pages; p++) {
                try {
                    JSONObject o = fetchPage(p);
                    JSONArray arr = o.optJSONArray("loadouts");
                    if (arr != null) for (int i = 0; i < arr.length(); i++) items.put(arr.getJSONObject(i));
                } catch (Throwable t) {
                    failed.add(String.valueOf(p));
                }
                emit("onProgress", pages + "," + p + "," + total + "," + items.length());
                try {
                    Thread.sleep(30);
                } catch (InterruptedException ignored) {
                }
            }

            String savedAt = new SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.CHINA).format(new Date());
            JSONArray merged = mergeWithCache(items);
            JSONObject cache = new JSONObject();
            cache.put("saved_at", savedAt);
            cache.put("items", merged);
            writeCache(cache.toString());

            fetching = false;
            emit("onDone", JSONObject.quote(savedAt) + "," + merged.length() + "," + new JSONArray(failed).toString());
        } catch (Throwable t) {
            fetching = false;
            String msg = t.getMessage() == null ? t.getClass().getSimpleName() : t.getMessage();
            emit("onError", JSONObject.quote(msg));
        }
    }

    private void doDailyFetch() {
        try {
            String url = "https://" + HOST + DAILY_PATH;
            JSONObject d = getJson(url, 3);
            JSONArray src = d.optJSONArray("items");
            JSONArray out = new JSONArray();
            if (src != null) {
                for (int i = 0; i < src.length(); i++) {
                    JSONObject o = src.optJSONObject(i);
                    if (o == null) continue;
                    JSONObject cell = new JSONObject();
                    cell.put("name", o.optString("name", ""));
                    cell.put("code", o.optString("code", ""));
                    out.put(cell);
                }
            }
            JSONObject cache = new JSONObject();
            cache.put("items", out);
            cache.put("date", d.optString("date", ""));
            cache.put("updatedText", d.optString("updatedText", ""));
            cache.put("isToday", d.optBoolean("isToday", false));
            cache.put("fetchedAt", new SimpleDateFormat("HH:mm:ss", Locale.CHINA).format(new Date()));
            writeFile(DAILY_NAME, cache.toString());

            dailyFetching = false;
            emit("onDaily", cache.toString());
        } catch (Throwable t) {
            dailyFetching = false;
            String msg = t.getMessage() == null ? t.getClass().getSimpleName() : t.getMessage();
            emit("onDailyError", JSONObject.quote(msg));
        }
    }

    private JSONObject getJson(String url, int tries) throws Exception {
        Exception last = null;
        for (int attempt = 0; attempt < tries; attempt++) {
            HttpURLConnection c = null;
            try {
                c = (HttpURLConnection) new URL(url).openConnection();
                c.setConnectTimeout(15000);
                c.setReadTimeout(25000);
                c.setRequestMethod("GET");
                c.setRequestProperty("Accept", "application/json, text/plain, */*");
                c.setRequestProperty("Accept-Language", "zh-CN,zh;q=0.9");
                c.setRequestProperty("Accept-Encoding", "gzip");
                c.setRequestProperty("User-Agent", UA);
                c.setRequestProperty("Connection", "keep-alive");
                int code = c.getResponseCode();
                if (code == 429) {
                    // 服务端 x-ratelimit-limit: 60，连续刷新会撞上限，退避重试
                    last = new Exception("HTTP 429 请求过于频繁");
                    try {
                        Thread.sleep(900L * (attempt + 1));
                    } catch (InterruptedException ignored) {
                    }
                    continue;
                }
                if (code != 200) throw new Exception("HTTP " + code);
                InputStream in = c.getInputStream();
                String enc = c.getContentEncoding();
                if (enc != null && enc.toLowerCase(Locale.US).contains("gzip")) {
                    in = new GZIPInputStream(in);
                }
                ByteArrayOutputStream bo = new ByteArrayOutputStream();
                byte[] buf = new byte[16384];
                int n;
                while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
                in.close();
                return new JSONObject(new String(bo.toByteArray(), "UTF-8"));
            } catch (Exception e) {
                last = e;
                try {
                    Thread.sleep(400);
                } catch (InterruptedException ignored) {
                }
            } finally {
                if (c != null) c.disconnect();
            }
        }
        throw last == null ? new Exception("未知网络错误") : last;
    }

    private String readFile(String name) {
        try {
            File f = new File(getFilesDir(), name);
            if (!f.exists()) return "";
            java.io.FileInputStream in = new java.io.FileInputStream(f);
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
            in.close();
            return new String(bo.toByteArray(), "UTF-8");
        } catch (Throwable t) {
            return "";
        }
    }

    /** 新数据优先，旧缓存里没被新数据覆盖的条目补在后面（与桌面版 merge_items 同逻辑）。
     *  这样某一页失败时不会把已有数据丢掉。 */
    private JSONArray mergeWithCache(JSONArray fresh) {
        JSONArray out = new JSONArray();
        java.util.HashSet<String> seen = new java.util.HashSet<String>();
        for (int i = 0; i < fresh.length(); i++) {
            JSONObject o = fresh.optJSONObject(i);
            if (o == null) continue;
            String k = o.optString("id", "");
            if (k.length() == 0) k = o.optString("code", "");
            if (k.length() > 0 && !seen.add(k)) continue;
            out.put(o);
        }
        try {
            String raw = readFile(CACHE_NAME);
            if (raw != null && raw.length() > 0) {
                JSONArray old = new JSONObject(raw).optJSONArray("items");
                if (old != null) {
                    for (int i = 0; i < old.length(); i++) {
                        JSONObject o = old.optJSONObject(i);
                        if (o == null) continue;
                        String k = o.optString("id", "");
                        if (k.length() == 0) k = o.optString("code", "");
                        if (k.length() > 0 && !seen.add(k)) continue;
                        out.put(o);
                    }
                }
            }
        } catch (Throwable ignored) {
        }
        return out;
    }

    private void writeCache(String text) {
        writeFile(CACHE_NAME, text);
    }

    private void writeFile(String name, String text) {
        try {
            File tmp = new File(getFilesDir(), name + ".tmp");
            FileOutputStream fo = new FileOutputStream(tmp);
            fo.write(text.getBytes("UTF-8"));
            fo.flush();
            fo.close();
            File dst = new File(getFilesDir(), name);
            if (dst.exists()) dst.delete();
            tmp.renameTo(dst);
        } catch (Throwable ignored) {
        }
    }

    private JSONObject fetchPage(int page) throws Exception {
        return getJson("https://" + HOST + API_PATH + "?page=" + page, 3);
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            try {
                web.removeJavascriptInterface("Native");
                web.destroy();
            } catch (Throwable ignored) {
            }
            web = null;
        }
        super.onDestroy();
    }
}
