# Repo Root Hygiene Report
- time: 2026-02-01 23:49:27
- repo: /Users/williamhsu/tmf_autotrader

## Summary
- KEEP*: 21
- MOVE_TO_QUARANTINE: 9
- REVIEW: 21

## MOVE_TO_QUARANTINE (candidates)

- "`ACKED`\357\274\210\347\263\273\347\265\261\345\233\236\345\240\261\345\247\224\350\250\227\346\210\220\347\253\213 (other, ~0B) — looks like scaffold/markdown artifact in repo root
- "`DRILL_REPORT_YYYYMMDD.md`\357\274\210\351\200\232\351\201\216 (other, ~0B) — looks like scaffold/markdown artifact in repo root
- "`UNKNOWN`\357\274\210\345\233\236\345\240\261\347\274\272\345\244\261 (other, ~0B) — looks like scaffold/markdown artifact in repo root
- "`hedge_instrument`\357\274\232TXF (other, ~0B) — looks like scaffold/markdown artifact in repo root
- "`roll_mode`\357\274\232\347\246\201\346\255\242\346\226\260\345\242\236\346\226\271\345\220\221\351\203\250\344\275\215\343\200\201\345\217\252\345\205\201\350\250\261\346\270\233\345\200\211 (other, ~0B) — looks like scaffold/markdown artifact in repo root
- `calendar (dir, ~255B) — looks like scaffold/markdown artifact in repo root
- `ops (dir, ~199B) — looks like scaffold/markdown artifact in repo root
- `research (dir, ~67B) — looks like scaffold/markdown artifact in repo root
- `risk (dir, ~61B) — looks like scaffold/markdown artifact in repo root

## REVIEW (needs decision)

- "Walk-forward\357\274\210\346\273\276\345\213\225\350\250\223\347\267\264 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\344\270\200\351\215\265\351\207\215\346\224\276\357\274\210replay\357\274\211\344\273\273\346\204\217\344\270\200\345\244\251\357\274\210\345\220\253\344\270\213\345\226\256 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\344\270\213\345\226\256 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\344\274\221\345\270\202\357\274\210\345\234\213\345\256\232\345\201\207\346\227\245 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\345\210\270\345\225\206\351\231\220\345\210\266\357\274\210\346\270\254\350\251\246 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\345\213\225\346\205\213\346\255\242\346\220\215 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\345\240\261\345\203\271\344\270\255\346\226\267 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\345\244\232\351\207\215\346\257\224\350\274\203\350\252\277\346\225\264\357\274\210\344\275\240\350\251\246\344\272\206\345\244\232\345\260\221\347\265\204\345\217\203\346\225\270 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\345\244\232\351\242\250\346\240\274\357\274\210Trend (other, ~0B) — not recognized as canonical; inspect before keeping
- "\346\230\216\347\242\272\350\262\273\347\224\250\357\274\232\346\211\213\347\272\214\350\262\273\343\200\201\346\234\237\344\272\244\346\211\200\350\262\273\347\224\250 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\346\234\237\350\262\250 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\346\234\254\346\251\237\347\206\261\351\215\265 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\347\240\224\347\251\266 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\350\213\245\350\241\214\346\203\205\344\270\215\345\217\257\347\224\250\357\274\232\347\246\201\346\255\242\351\226\213\346\226\260\345\200\211\343\200\201\345\217\252\345\205\201\350\250\261\346\270\233\345\200\211 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\350\250\202\345\226\256\347\255\226\347\225\245\357\274\210\344\273\245\343\200\214\351\231\215\344\275\216\346\213\222\345\226\256 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\350\255\211\345\210\270 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\351\232\261\345\220\253\346\210\220\346\234\254\357\274\232spread\343\200\201slippage\343\200\201impact\357\274\210\351\232\250\346\263\242\345\213\225 (other, ~0B) — not recognized as canonical; inspect before keeping
- "\351\242\250\351\232\252\351\240\220\347\256\227\347\250\213\345\274\217\345\214\226\357\274\232\346\257\217\347\255\226\347\225\245\346\227\245\350\231\247 (other, ~0B) — not recognized as canonical; inspect before keeping
- "canary\357\274\232\351\231\220\345\217\243\346\225\270 (other, ~0B) — not recognized as canonical; inspect before keeping
- "runbook\357\274\232connectivity (other, ~0B) — not recognized as canonical; inspect before keeping
- "urgency\357\274\210low (other, ~0B) — not recognized as canonical; inspect before keeping

## KEEP_CANON (expected)

- .gitignore (file, ~170B)
- DPB (dir, ~127B)
- MANIFEST_SHA256_ALL_FILES.txt (file, ~289KB)
- README.md (file, ~252B)
- TXF (dir, ~138B)
- broker (dir, ~2KB)
- calendar (dir, ~3KB)
- configs (dir, ~697B)
- contracts (dir, ~2KB)
- docs (dir, ~4MB)
- execution (dir, ~8KB)
- ops (dir, ~21KB)
- repo (dir, ~36KB)
- research (dir, ~2KB)
- risk (dir, ~3KB)
- runtime (dir, ~134MB)
- schemas (dir, ~842B)
- scripts (dir, ~265KB)
- snapshots (dir, ~1002B)
- spec (dir, ~8KB)
- src (dir, ~153KB)
