# Log Matrix Export Documentation

## Purpose
The `json_log_to_excel` function transforms structured trading logs from **filtered_log.json** into two export formats:

- **log_matrix.csv** → lightweight, token-efficient format for automated pipelines and LLM input.
- **log_matrix.xlsx** → human-friendly format for analysts, enabling filtering, sorting, and visualization.

The primary purpose of these exports is to **save tokens** when working with large language models (LLMs).
To reduce repetition, the **datetime** column uses a shorthand marker `~` for repeated timestamps.

---

## ⏱️ Datetime Representation

- **First row of a new timestamp** → full datetime string (e.g., `2026.01.02 01:00`).  
- **Subsequent rows with the same timestamp** → `~` marker.  
- This ensures only one full datetime per block, saving tokens while keeping rows aligned.

### Example
```
2026.01.02 01:00,ORDERINFO,0.0,0.0,...
~,ATRSL1buf,2.0,4335.86,4349.44,...
~,M5,1.0,511.0,1.0,...
2026.01.02 01:05,ORDERINFO,0.0,0.0,...
~,ATRSL1buf,2.0,4321.4,4335.84,...
```
---

## File Structure

### Columns
- **datetime** → Timestamp of the log entry.
- **category** → Source category (`ORDERINFO`, `TRADEINFO`, `ATRSL1buf`, `BBTFImpact`).
- **headers** → Merged attributes across categories, simplified into prefixed groups.
- **rows** → Values aligned to headers, either scalars or compact arrays (`{M5=7.83|M30=0.19|H1=6.07}`).

---

## TRADEINFO Log Format (v22.22+)

Every `[TRADEINFO]` line uses a structured key:value format with pipe-delimited gate segments:

```
[TRADEINFO] Gate:[GATENAME] TradeAct:N key:val key:val| Gate:[GATENAME] key:val|act:N atrsl:N
```

### Format Rules
- **First segment**: always `Gate:[NAME] TradeAct:N` followed by gate-specific key:value pairs
- **Subsequent segments**: `| Gate:[NAME] key:value...` (no `TradeAct` — belongs to first gate only)
- **Final suffix**: `|act:N atrsl:N` where `act` is the resolved Trade_Act and `atrsl` is the ATRSL direction
- `TradeAct` = value of Trade_act at the moment that gate was evaluated (intent)
- `act` = final resolved action (0=hold, 1=BUY, 2=SELL, 7=exit_all)

### Parsing Recipe
```python
# Strip prefix and suffix
line = raw.replace("[TRADEINFO] ", "")
# Split trailing act/atrsl
body, suffix = line.rsplit("|act:", 1)
act, atrsl = suffix.split(" atrsl:")
# Split gate segments
segments = [s.strip() for s in body.split("|")]
# Parse each segment
for seg in segments:
    tokens = seg.split()
    gate = tokens[0]          # "Gate:[G1-OK]"
    pairs = tokens[1:]        # ["TradeAct:0", "M30:1", "M15:5"]
```

---

## Gate Reference — TRADEINFO Attributes

### Early-return gates (single segment, full line)

| Gate | Key attributes |
|------|---------------|
| `Gate:[G0d-COOL]` | `TradeAct:N cd:N` — bars remaining in post-exit cooldown |
| `Gate:[G0]` | `TradeAct:N M30:N M15:N H1:N` — dual sideway exit |
| `Gate:[G0-HOLD]` | `TradeAct:N M30:N M15:N H1:N` — sideway but H1 trending, hold |
| `Gate:[G0b-PINK]` | `TradeAct:N M30+M15_SQZ` — both SQZ simultaneously |
| `Gate:[G0b-ATRSL]` | `TradeAct:N reason:ATRSL_dn/up dir:BUY/SELL` |
| `Gate:[G0b-M15OPP]` | `TradeAct:N M15stg:N M15mid:N` |
| `Gate:[G0b-H4OPP]` | `TradeAct:N H4stg:N H4mid:N` |
| `Gate:[G0b-M30OPP]` | `TradeAct:N M30stg:N M30mid:N` — M30 opposing fly/shrink (523 flat mid v22.29) |
| `Gate:[G0b-M5OPP]` | `TradeAct:N M5stg:N M5mid:N` — M5 sole shrink trigger (cas_shrinkTF==0) with M5 mid opposing direction (v22.31) |
| `Gate:[G0b-M5FLY]` | `TradeAct:0 M5stg:N cas_shrinkTF:N` — M5 in committed opposing fly (521/522 vs BUY; 511/512 vs SELL) when cas_shrinkTF>0 (RC28b, v22.41) |
| `Gate:[G0b-M5SHRKopp]` | `TradeAct:0 M5stg:N M5mid:N cas_shrinkTF:N` — M5 in opposing bearish shrink (523 mid∈{2,3,4} vs BUY) or bullish shrink (513 mid∈{1,3,5} vs SELL) when cas_shrinkTF>0 (RC34, v22.44) |
| `Gate:[G0b-H1OPP]` | `TradeAct:0 H1stg:N H1mid:N` — H1 committed fly (511/512/521/522) incl. flat mid=3 opposing cascade direction (RC36, v22.46) |
| `Gate:[G0b-SQZLOCK]` | `TradeAct:N H1_SQZ+M30_SQZ+both_flat` — H1+M30 both SQZ both mid==3 |
| `Gate:[G0b-TOUCH]` | `TradeAct:N TF:N touch:upper_band/lower_band sl:N.NN` |
| `Gate:[G0b-WAIT]` | `TradeAct:N TF:N` — shrink+SQZ active but no band touch yet |
| `Gate:[G0c-SQZLOCK]` | `TradeAct:N H1_SQZ:M30_cmp/M15_SQZ` |
| `Gate:[G5-FADE]` | `TradeAct:N M5:prevN>curN` — M5 fading, exit |
| `Gate:[G7-NOTM15BAR]` | `TradeAct:N m5off:N` — entry not on last M5 bar of M15 period (m5_start - m15_start < 600s), blocked (DimGray) |
| `Gate:[G7-H1OPP]` | `TradeAct:N H1:N` — cases 3/4 blocked by H1 opposing |
| `Gate:[PHASE2-WAIT]` | `TradeAct:N bars:N/3` |
| `Gate:[PHASE2-BUY]` | `TradeAct:N bars:N sl:N.NN` |
| `Gate:[PHASE2-SELL]` | `TradeAct:N bars:N sl:N.NN` |
| `Gate:[PHASE2-CANCEL]` | `TradeAct:N reason:buy_gone/sell_gone` |

### Multi-segment fly/shrink logs (pipe-delimited)

```
[TRADEINFO] Gate:[G1-OK] TradeAct:0 M30:1 M15:5| Gate:[FLY] dir:1 sl:3248.00 H2L:-1/-1 L2H:2/-1|act:1 atrsl:0
[TRADEINFO] Gate:[H4-SQZ] TradeAct:0| Gate:[G1-OK] M30:1 M15:1| Gate:[G4-BLOCK] M15:2| Gate:[G7-NEUTRAL]|act:0 atrsl:1
[TRADEINFO] Gate:[H4-OPPOSE] TradeAct:0 H4_dn:2| Gate:[G7-NEUTRAL]|act:0 atrsl:1
[TRADEINFO] Gate:[G6-SHRINK] TradeAct:0 cnt:2+M5 pen:0.75| Gate:[G5] c:1 p:3 p2:3 M15s:511 M15m:1 t:flat_up mid+ abv M15ok q:90 sz:1.0| Gate:[G6-BUY] sl:3250.50|act:1 atrsl:0
```

| Gate segment | Key attributes |
|---|---|
| `Gate:[H4-OPPOSE]` | `TradeAct:N H4_dn:N` or `H4_up:N` — H4 macro filter blocked |
| `Gate:[H4-SQZ]` | `TradeAct:N` — H4 in SQZ, trade allowed through |
| `Gate:[G1-FAIL]` | `M30:N M15:N` (+ `TradeAct:N` if first gate) |
| `Gate:[G1-OK]` | `M30:N M15:N` (+ `TradeAct:N` if first gate) |
| `Gate:[G4-BLOCK]` | `M15:N` — M15 hard conflict |
| `Gate:[FLY]` | `dir:N sl:N.NN H2L:N/N L2H:N/N` |
| `Gate:[G7-NEUTRAL]` | (no params) — no chain match |
| `Gate:[G7-NOCHAIN]` | (no params) — M5-only, no H1+ chain |
| `Gate:[G7-SUPPRESSED]` | (no params) — lot below minimum |
| `Gate:[PHASE1-BUY]` | (no params) — reversal intercepted, pending buy |
| `Gate:[PHASE1-SELL]` | (no params) — reversal intercepted, pending sell |
| `Gate:[G7-TOOSOON]` | `bars:N<DynMinHold` — min hold bars not met (dynamic: M5=3, M15=6, M30=12, H1=18) |
| `Gate:[G6-SHRINK]` | `cnt:N+M5 pen:N.N` — shrink path prefix |
| `Gate:[G5]` | `c:N p:N p2:N M15s:N M15m:N t:TYPE [mid+] [abv] [M15ok] q:N sz:N.N` — M5 transition |
| `Gate:[G6-BUY]` | `sl:N.NN` |
| `Gate:[G6-SELL]` | `sl:N.NN` |
| `Gate:[G6-REV]` | `M5:N` — M5 opposing during shrink, exit |
| `Gate:[G4d-M30SID]` | logged in shrink path when M30 flat + M15 opposing |
| `Gate:[G4c-M15OPP]` | `M15stg:N M15mid:N` — M15 opposing fly/shrink blocked in shrink path |
| `Gate:[G4e-H4OPP]` | `H4stg:N H4mid:N` — H4 macro opposing in shrink path |
| `Gate:[G4f-M30OPP]` | `M30stg:N M30mid:N` — M30 macro opposing in shrink path (SQZ v22.27) |
| `Gate:[G4k-M5SHRKopp]` | `M5stg:N M5mid:N` — adaptive trigger active (trigTF>0) + M5 in opposing shrink (523 mid∈{2,3,4} for BUY; 513 mid∈{1,3,5} for SELL) (RC30, v22.43) |
| `Gate:[G4k-TRIGDIR]` | `trigTF:N stg:N` — adaptive trigger TF stage contradicts direction (511/512 bullish + SELL; 521/522 bearish + BUY) (RC31, v22.43) |
| `Gate:[G4k-M5STG]` | `M5stg:N M5mid:N` — M5 sole trigger (trigTF=0) + M5 structural stage contradicts direction (513+SELL always; 523+BUY mid∈{2,3,4}) (RC32, v22.44) |

### Gate:[G5] — M5 Transition Detail

The `t:` field encodes the transition type:

| t: value | Meaning | Base quality |
|---|---|---|
| `flat_up` | FLAT→UP | 70 |
| `flat_dn` | FLAT→DN | 70 |
| `up_dn` | UP→DN reversal | 75 |
| `dn_up` | DN→UP reversal | 75 |
| `weak_up` | FLAT→SIDEUP | 45 |
| `weak_dn` | FLAT→SIDEDN | 45 |
| `sqz_brk_up` | SQZ break upward | 75 |
| `sqz_brk_dn` | SQZ break downward | 75 |

Quality boosters (each appended to t: field if active): `mid+`, `abv`, `M15ok`, `cok`

Quality suppressors (appended when quality capped): `noM15` — sqz_brk transition when confirmTF mid=3 (flat), quality capped at 59 → blocked (RC39, v22.48)

Quality → size multiplier: `≥90→1.0` | `≥75→0.75` | `≥60→0.5` | `≥45→0.25` | `<45→0.0`

---

## Categories and Header Construction

### Categories
- **ORDERINFO** → Trade order details (profit, lots, tickets, etc.)
- **TRADEINFO** → Trade execution metadata (Gate, TradeAct, act, atrsl, sl, dir, etc.)
- **ATRSL1buf** → ATR stop-loss buffer values (Trend, LV, Upper, Lower)
- **BBTFImpact** → Bollinger Band timeframe impact (Sideway_val, HTF/LTF drive)
- **NEW_ORDER_OPEN / NEW_ORDER_CLOSE** → Order lifecycle attributes
- **timeframe_cats = {"M5","M15","M30","H1","H4","D1","W1"}** → Collapsed into `TF-*` headers

### Header Construction
Each header is a merged path linking multiple categories:
```
ORDERINFO-BUY_PROFIT/ATRSL1buf-Trend/BBTFImpact-Sideway_val/TF-first_stage/TRADEINFO-Gate/NEW_ORDER_OPEN-OPEN_TICKET
```

For `TRADEINFO`, the primary parse keys are: `Gate`, `TradeAct`, `act`, `atrsl`, `sl`, `dir`, `M30`, `M15`, `H1`, `H4`, `q`, `sz`, `t`

---

## Tracking Issues

When anomalies are found in log_matrix.csv or log_matrix.xlsx:

1. **Header–Category Mapping** — Verify each header links to its correct category. `TF-first_stage` must only come from timeframe categories.
2. **Row Value Alignment** — Check that `TRADEINFO-Gate` and `TRADEINFO-act` match the intended gate and final action.
3. **Cross-File Validation** — Compare the same row in CSV and Excel. If values differ, the issue is in export formatting.
4. **Source JSON Check** — Trace anomalies back to filtered_log.json.
5. **Debugging Workflow** — Print `attr_dict` during Pass 2. Log `headers_simple` after simplification. Test with minimal JSON samples.

---

## Best Practices
- Always keep both `log_matrix.csv` and `log_matrix.xlsx` for comparison.
- Use CSV for machine checks, Excel for human review.
- Document anomalies with **timestamp + Gate + act**.
- For TRADEINFO parsing: always split on `|` first, then parse each segment's key:value pairs.
- The `TradeAct` key only appears in the **first** gate segment per line.
- `act` and `atrsl` are always in the **final suffix** after the last `|`.
