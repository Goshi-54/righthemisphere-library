// 調整ツールの計算（ページの表示と書き出し用スクリプト apply.py で同じ式を使う）
// 値はどれも -100〜100 の整数。0 で何もしない。
(function (root) {
  'use strict';

  var DEFAULTS = { exposure: 0, contrast: 0, highlights: 0, shadows: 0, texture: 0, clarity: 0 };

  // 明瞭度：大きくぼかした像との差を足す（3回の箱型ぼかし ≒ ガウスぼかし σ20px）
  var CLARITY_RADII = [19, 19, 20];
  var CLARITY_GAIN = 0.6;
  // テクスチャ：細かくぼかした像との差を足す（≒ σ1.5px）
  var TEXTURE_RADII = [1, 1, 1];
  var TEXTURE_GAIN = 1.2;

  function smooth(e0, e1, x) {
    var t = (x - e0) / (e1 - e0);
    t = t < 0 ? 0 : t > 1 ? 1 : t;
    return t * t * (3 - 2 * t);
  }

  // 明るさの曲線（0〜1 → 0〜1）
  function tone(v, p) {
    v = v * Math.pow(2, p.exposure / 100);          // 露光量 ±1EV
    v = 0.5 + (v - 0.5) * (1 + p.contrast / 100);    // コントラスト（中間の灰色を軸に）
    v = v + (p.highlights / 100) * 0.25 * smooth(0.5, 1, v);       // ハイライト
    v = v + (p.shadows / 100) * 0.25 * (1 - smooth(0, 0.5, v));    // シャドウ
    return v < 0 ? 0 : v > 1 ? 1 : v;
  }

  function buildLut(p) {
    var L = new Uint8Array(256);
    for (var i = 0; i < 256; i++) L[i] = Math.floor(tone(i / 255, p) * 255 + 0.5);
    return L;
  }

  function amount(v, gain) { return Math.round((v / 100) * gain * 10000) / 10000; }

  // ffmpeg avgblur と同じ：横→縦の順に平均（端は端の画素を伸ばす）、最後に切り捨て
  function box2d(src, dst, w, h, r, tmp) {
    var x, y, o, s, d, q, inv = 1 / (2 * r + 1);
    for (y = 0; y < h; y++) {
      o = y * w; s = 0;
      for (d = -r; d <= r; d++) { q = d < 0 ? 0 : d >= w ? w - 1 : d; s += src[o + q]; }
      for (x = 0; x < w; x++) {
        tmp[o + x] = s * inv;
        q = x + r + 1; s += src[o + (q >= w ? w - 1 : q)];
        q = x - r; s -= src[o + (q < 0 ? 0 : q)];
      }
    }
    for (x = 0; x < w; x++) {
      s = 0;
      for (d = -r; d <= r; d++) { q = d < 0 ? 0 : d >= h ? h - 1 : d; s += tmp[q * w + x]; }
      for (y = 0; y < h; y++) {
        dst[y * w + x] = Math.floor(s * inv);
        q = y + r + 1; s += tmp[(q >= h ? h - 1 : q) * w + x];
        q = y - r; s -= tmp[(q < 0 ? 0 : q) * w + x];
      }
    }
  }

  // a に「a − ぼかし」を amt 倍して足す（a を書き換える）
  function unsharp(a, w, h, radii, amt, t1, t2, tf) {
    t1.set(a);
    for (var k = 0; k < radii.length; k++) {
      box2d(t1, t2, w, h, radii[k], tf);
      t1.set(t2);
    }
    for (var i = 0, n = w * h; i < n; i++) {
      var v = a[i] + amt * (a[i] - t1[i]) + 0.5;
      v = v < 0 ? 0 : v > 255 ? 255 : v;
      a[i] = v | 0;
    }
  }

  var buf = { n: 0 };
  function buffers(n) {
    if (buf.n !== n) {
      buf = { n: n, r: new Uint8Array(n), g: new Uint8Array(n), b: new Uint8Array(n), t1: new Uint8Array(n), t2: new Uint8Array(n), tf: new Float32Array(n) };
    }
    return buf;
  }

  // rgba（Uint8ClampedArray, 幅w×高さh）→ out（同じ形）
  function processRGBA(rgba, out, w, h, p) {
    var n = w * h, B = buffers(n), lut = buildLut(p), i, j;
    for (i = 0, j = 0; i < n; i++, j += 4) { B.r[i] = lut[rgba[j]]; B.g[i] = lut[rgba[j + 1]]; B.b[i] = lut[rgba[j + 2]]; }
    var chs = [B.r, B.g, B.b];
    if (p.clarity) { var ca = amount(p.clarity, CLARITY_GAIN); for (i = 0; i < 3; i++) unsharp(chs[i], w, h, CLARITY_RADII, ca, B.t1, B.t2, B.tf); }
    if (p.texture) { var ta = amount(p.texture, TEXTURE_GAIN); for (i = 0; i < 3; i++) unsharp(chs[i], w, h, TEXTURE_RADII, ta, B.t1, B.t2, B.tf); }
    for (i = 0, j = 0; i < n; i++, j += 4) { out[j] = B.r[i]; out[j + 1] = B.g[i]; out[j + 2] = B.b[i]; out[j + 3] = 255; }
    return out;
  }

  var api = {
    DEFAULTS: DEFAULTS, tone: tone, buildLut: buildLut, processRGBA: processRGBA, amount: amount,
    CLARITY_RADII: CLARITY_RADII, CLARITY_GAIN: CLARITY_GAIN, TEXTURE_RADII: TEXTURE_RADII, TEXTURE_GAIN: TEXTURE_GAIN
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.AdjustCore = api;
})(this);
