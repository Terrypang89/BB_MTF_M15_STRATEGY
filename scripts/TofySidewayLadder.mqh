#property copyright "Copyright 2026, terrypang."
#property link      "https://www.mql5.com/en/users/terrypang/"
#property version   "38.17"

#define HAS_TOFYSIDEWAY_LADDER
//+------------------------------------------------------------------+
//| TofySidewayLadder.mqh   -- DIAGNOSTIC ONLY                        |
//|                                                                  |
//| Computes the proposed sequential sideway LADDER and draws a label |
//| on every M15 bar so the flow can be verified visually.            |
//|                                                                  |
//| IT DOES NOT TRADE AND DOES NOT WRITE sideway_selected.            |
//| It writes only its own field so the existing detector and DMONLY  |
//| are completely unaffected. Run both in parallel, compare, and     |
//| only then decide whether the ladder should drive anything.        |
//|                                                                  |
//| LADDER (each step needs the PREVIOUS bar one level below):        |
//|   state 1  M15 : A15 and B15                                      |
//|   state 2  M30 : prev==1 and A30 and B30                          |
//|   state 3  H1  : prev==2 and A1H and B1H and C1H                  |
//|                                                                  |
//|   A15 = (clus0[LA] < clus0[LA_1] < clus0[LA_2]) OR                |
//|         (clus0[LA] < CL_NEAR and clus0[LA_1] < CL_NEAR)           |
//|   B15 = stage[1][LA] in (512,523,4xx) OR                          |
//|         (dmid[1][LA] < dmid[1][LA_1] < dmid[1][LA_2])             |
//|   A30/B30 same shape on clus1 and index 2                         |
//|   A1H = stage[3][LA] in (512,523,4xx) OR dbbw[3] decreasing       |
//|   B1H = clus2[LA] < clus2[LA_1] < clus2[LA_2]                     |
//|   C1H = clus1[LA] < CL_NEAR and clus1[LA_1] < CL_NEAR             |
//|                                                                  |
//| MEASURED on 20260712_clean.log (baseline QUIET 37.8%):            |
//|   state 1  n=2904  QUIET 41.4%  (+3.6)                            |
//|   state 2  n= 948  QUIET 48.0%  (+10.2)   <- best                 |
//|   state 3  n= 229  QUIET 41.0%  (+3.2)    <- DEGRADES             |
//|   current S_ flag  n=1681  QUIET 53.9%  (+16.1)                   |
//| On the 2026.02.03 12:40 - 02.04 02:05 choppy range (50 bars):     |
//|   current S_ covered  6/50 (12%)                                  |
//|   ladder state>=1    23/50 (46%)  but it fires on 38% of ALL bars |
//|                                                                  |
//| FIELD NAMES: BBW_stage and BB_midline_Cluster are confirmed from  |
//| existing code. BB_diffMid and BB_diffBBW are INFERRED from the    |
//| log field names diffMid_M15 / diffBBW_H1 -- if the compiler       |
//| rejects them, substitute the real struct member names.            |
//+------------------------------------------------------------------+

//--- ladder settings
bool   SL_Draw      = true;     // draw the ladder label

//--- Level-1 diagnostic tags, appended to the chart label and the [LADDER] line.
//--- These do NOT change any decision - they only report which level-1 shapes are
//--- present on the bar, so the chart shows WHY a bar did or did not reach state 1.
//---   L1A  S15 && dm1 >= 3            stage says settled but the midlines are apart
//---   L1B  dm1 < dm1a < dm1b          midline distance is contracting, 3 bars
//---   L1C  dm1>=3 && dm1a>=3 && one of them == 3   sitting right at the threshold
//---   L1D  W15                        M15 band width is contracting
bool   SL_DrawL1Tags = true;

//--- Level-2 (M30) diagnostic tags. Same idea as the L1 tags, on the M30 side.
//---   L2A  S30            M30 stage is in the settled set
//---   L2B  dm2<dm2a<dm2b  M30 midline distance contracting, 3 bars
//---   L2C  dm2>=3 && dm2a>=3 && any of dm2/dm2a/dm2b == 3
//---   L2D  W30            M30 band width contracting, 2 bars
//--- A30 is deliberately NOT tagged - the cluster gate is reported by `why`.
//--- Reporting only. Nothing here changes a decision.
bool   SL_DrawL2Tags = true;
bool   SL_DrawL3Tags = true;    // H1 tags, drawn on the H1 midline at the H1 bar time
bool   SL_DrawL4Tags = true;    // H4 tags, drawn on the H4 midline at the H4 bar time
color  SL_L1TagColor = Goldenrod; 
color  SL_L2TagColor = GreenYellow; 
color  SL_L3TagColor = Red;
color  SL_L4TagColor = Yellow;

//--- Vertical offset for the tag labels, in POINTS above the midline they belong to.
//--- Drawn exactly on the midline the text collides with the band traces, so lift it
//--- clear. On XAUUSD _Point is 0.01, so 500 points = $5.00. Raise it if the chart is
//--- zoomed out, lower it if the labels float too far from their line.
int    SL_TagOffsetPts = 500;
bool   SL_WriteLog  = true;     // emit [LADDER] log lines
int    SL_FontSize  = 10;
double SL_Angle     = 90.0;     // OBJPROP_ANGLE is a DOUBLE property
// double CL_NEAR      = 10.5;     // 10.0 rejected clus1 = 10.1 by 0.1 and broke
                                // the ladder chain. 10.5 costs +89 bars and takes
                                // the 2026.02.03 window from 16/50 to 27/50.
double CL_NEAR_M15    = 10.5;     // 10.0 rejected clus1 = 10.1 by 0.1 and broke
double CL_NEAR_M30    = 8;     // 10.0 rejected clus1 = 10.1 by 0.1 and broke
double CL_NEAR_H1     = 30;     // 10.0 rejected clus1 = 10.1 by 0.1 and broke
double CL_NEAR_H4     = 0;
//+------------------------------------------------------------------+
//| TRADE STRATEGY (optional)                                        |
//|                                                                  |
//| Trade_Strategy() below is DMONLY with one substitution:    |
//| the sideways exit fires on the LADDER (SL_state[LA] >= 2) instead |
//| of the TofySideway S_ flag. Everything else - entries, reversals, |
//| priority order, the once-per-bar guard - is identical to          |
//| TofyTrade_DMonly.mqh.                                             |
//|                                                                   |
//| SL_UseTradeStrategy = false  -> the function returns HOLD         |
//|                                 immediately and changes nothing.  |
//| SL_UseTradeStrategy = true   -> the ladder drives the exits.      |
//|                                                                   |
//| MEASURED against references/SIDEWAY_LABELS_FEB.md (858 of 1830    |
//| February bars labelled sideway):                                  |
//|   TofySideway S_   precision 82.4%  recall 33.2%  fires 346       |
//|   ladder state>=2  precision 70.4%  recall 60.3%  fires 734       |
//| The ladder fires roughly TWICE as often. The DMONLY churn         |
//| analysis found 844 trades held 1-5 bars lost -$2,258 while 276    |
//| held 6+ bars made +$3,227 - so more exits means shorter holds,    |
//| which has been the LOSING direction. Whether the ladder's better  |
//| recall outweighs that is exactly what this is here to measure.    |
//| It has NOT been measured yet.                                     |
//+------------------------------------------------------------------+
bool   SL_UseTradeStrategy = true;   // off by default - changes nothing until enabled

//--- which signal drives the sideways exit when the above is true
//---   0 = ladder only          SL_state[LA] >= 2
//---   1 = TofySideway only     sideway_selected[LA] > 0   (= plain DMONLY)
//---   2 = BOTH must agree      fewest exits, longest holds
//---   3 = EITHER fires         most exits
//---   4 = HAND LABELS          hindsight ceiling, NOT tradeable
int    SL_ExitMode = 0;

//--- Which bar Trade_Strategy decides on.
//---   0 = M5  - three times the decision points
//---   1 = M15 - one decision per ladder update
//--- The measured figures (+415.36 for diffMid_Trend_M15, +1353.85 for
//--- diffMid_Trend_M5 against the hand labels) were simulated at M15 spacing with
//--- the chosen dm value forward-filled. M5 spacing is a DIFFERENT strategy and has
//--- not been measured - the churn analysis found short holds losing consistently,
//--- so more decision points is not automatically better.
int    SL_TradeTF = 1;

//--- Which timeframe's diffMid_Trend drives ENTRIES and REVERSAL exits.
//---   0 = M5 (BB_datas[0])
//---   1 = M15 (BB_datas[1])  <- default, unchanged behaviour
//--- Measured on February against the hand labels, same sideway signal both times:
//---   M15   58 trades  44.8% win   +415.36
//---   M5    99 trades  56.6% win  +1353.85
//--- Hit rates 45.7% vs 47.8% - both under 50%, so this is a narrow edge on a
//--- concentrated set of trades, measured on the month the labels came from.
//--- SEPARATE from SL_TradeTF, which controls how OFTEN the strategy decides.
//--- The measured figures used M15 decision spacing (SL_TradeTF = 1) with the
//--- chosen dm value - so M5 trend + M15 spacing is the tested combination.
int    SL_TrendTF = 1;

bool   SL_UseH1     = false;    // measured to DEGRADE the ladder; off by default
// double SL_diffmid_m15 = 3;
// double SL_diffmid_m30 = 1.5;
double SL_diffmid_m15 = 1.5;
double SL_diffmid_m30 = 2.3;
double SL_diffmid_H1  = 3.4;
double SL_diffmid_H4  = 7.7;

//--- LEVEL 1 evidence gate. Measured (L2Mode 0, BreakoutMode 1):
//---   0  A15 && (S15 || C15)   n=3158 (42%) lift +11.2  window 25/50  enrich 1.20x
//---   1  A15 && C15            n=3139 (41%) lift +11.5  window 25/50  enrich 1.21x  <- default
//---   2  A15 && S15            n=2353 (31%) lift +13.4  window 21/50  enrich 1.36x
//---   3  A15 && S15 && C15     n=2334 (31%) lift +13.8  window 21/50  enrich 1.37x
//--- Mode 1 beats mode 0 on lift AND enrichment at identical window coverage, and
//--- removes a false positive at 2026.02.04 05:15-05:30 where S15 was true while
//--- price ran 23-30 points.
int    SL_L1Mode = 1;

//--- LEVEL 2 evidence gate (always ANDed with prev >= 1 and A30):
//---   0  S30 || C30 || W30     n=3139 (41%) lift +11.5  window 25/50  <- default
//---   1  S30 || C30            n=2701 (35%) lift +13.3  window 19/50
//---   2  C30 only              n=2384 (31%) lift +14.7  window 11/50
//--- Higher modes are more precise but cover the target range worse.
int    SL_L2Mode = 1;

//--- A close outside the M15 band means the range has broken, so the sideway
//--- state is cancelled. MEASURED (with CL_NEAR 10.5):
//---   no cancel   n=3756 (49% of bars) lift +8.4
//---   M30 cancel  n=3145 (41% of bars) lift +9.8
//---   M15 cancel  n=2891 (38% of bars) lift +12.1   <- used here
//--- Sequential variants were worse: M15-then-M30 +9.2, M15-AND-M30 +10.0.
//--- M15 bands are tighter: they break earlier and re-contain earlier, which
//--- tracks price better than the lagging M30 band.
//--- Breakout cancel mode. A close outside the M15 band means the range broke.
//--- MEASURED (CL_NEAR 10.5, baseline QUIET 37.8%):
//---   0 off                n=3756 (49%) lift  +8.4  window 27/50  flips   0
//---   1 brk               n=2891 (38%) lift +12.1  window 21/50  flips 887  <- default
//---   2 brk 2 bars        n=3423 (45%) lift  +9.5  window 22/50  flips 406
//---   3 brk AND !B15      n=3657 (48%) lift  +9.4  window 21/50  flips 172
//--- Mode 1 is the most precise but flickers (flag toggles on ~12% of bars).
//--- Modes 2 and 3 are steadier and cost ~2.7 lift points. Flicker is cosmetic while
//--- this module drives nothing; it would matter if it ever drove an exit.
//--- Breakout cancel. Modes 5-9 add the M30 band and the sequential forms.
//--- MEASURED on February, M5 trend, paired across 48 ladder settings:
//---   mode  median   worst    beats mode 1
//---   0     +231.18  + 88.97   8/48    off entirely
//---   1     +310.36  + 50.70    -      best median, weakest floor
//---   2     +287.32  +173.49  14/48
//---   5     +273.77  + 91.76   6/48
//---   6     +304.76  + 44.80   2/48
//---   7     +272.00  + 97.66   4/48
//---   8     +290.68  +171.84  20/48   best mean of all (+294.67)
//---   9     +301.39  +173.78  20/48   at SL_BrkLookback = 2
//--- The consistent effect is CONFIRMATION - requiring two bars or two
//--- timeframes lifts the worst case from ~+50 to ~+173 for about $20 of
//--- median. Which form is used looks arbitrary; the confirmation is not.
//--- NOTE mode 9's reversed control (M30 then M15) scored +294.10 - nearly
//--- identical - so the ORDER carries little information. The gain comes
//--- from needing two events, not from the sequence.
int    SL_BreakoutMode = 0;

//--- How many bars back modes 8/9 look for the first breakout of the pair.
int    SL_BrkLookback  = 2;

//--- W30 dbbw < 1 fires +4.4 and is now part of the level-2 evidence gate.
//--- Threshold value barely matters: <0 <1 <2 <5 all give the same result.
double SL_diffbbw_m15 = 1.0;
double SL_diffbbw_m30 = 1.0;    // W30 threshold
// double SL_diffbbw_H1  = 1.0;    // WH1 threshold (L3W)
double SL_diffbbw_H1  = 6.5;    // WH1 threshold (L3W)
double SL_diffbbw_H4 = 1.0;   // L4W tag only. MEASURED: no threshold separates
                              // sideway on H4 - best F1 58.1 at thr 156, firing on
                              // 97% of bars at 41% precision. Left at 1.0 because
                              // the value does not matter. Do not tune this.

//--- add near the other settings
bool SL_ShowFails = true;    // draw gray L0-A/L0-B labels for undetected bars


//+------------------------------------------------------------------+
//| HAND-LABELLED SIDEWAY RANGES (visual overlay + optional signal)  |
//|                                                                  |
//| The ranges from references/SIDEWAY_LABELS_FEB.md.                |
//|                                                                  |
//| TWO uses, both opt-in:                                            |
//|   SL_DrawUserLabels  - draw them as rectangles behind the candles |
//|   SL_ExitMode == 4   - use them AS the sideway signal             |
//|                                                                  |
//| MEASURED (February, DMONLY entries, gross):                       |
//|   labels as the signal   58 trades  +415.36   <- CEILING          |
//|   best ladder setting    64 trades   -66.13                       |
//|   TofySideway S_ flag   159 trades   -70.74                       |
//|   no sideway exit       114 trades  -636.37   <- FLOOR            |
//|                                                                   |
//| ############ THE LABELS ARE HINDSIGHT ############                |
//| SL_ExitMode 4 is NOT TRADEABLE. It knows the answer in advance.   |
//| It exists only to measure the ceiling on a backtest. Never run it |
//| forward, and never treat +415.36 as a target - it is headroom.    |
//| ##################################################                |
//+------------------------------------------------------------------+
bool   SL_DrawUserLabels = true;   // draw the labelled ranges on the chart
color  SL_LabelColor     = clrViolet;   // pink
bool   SL_LabelFill      = false;

//--- Draw each trade as a segment from entry to exit, tagged with its P&L.
//--- Together with the range rectangles this reproduces on the chart what the
//--- "Combined timeline" table in SIDEWAY_LABELS_CEILING_FEB.md shows:
//---   shaded rectangle = a sideway range, flat, sitting out
//---   green/red segment = a position, with its P&L
//--- Prices are the M5 close at the signal bar, the same basis the Python
//--- simulation uses, so the on-chart P&L matches the report.
bool   SL_DrawTrades   = true;
color  SL_WinColor     = clrLime;
color  SL_LossColor    = clrRed;
int    SL_TradeWidth   = 2;
int    SL_TradeFont    = 8;

//--- Hand-labelled sideway ranges from references/SIDEWAY_LABELS_FEB.md
//--- Extend this array when a new month is labelled. Format "YYYY.MM.DD HH:MM".
#define SL_LABEL_COUNT 27
string SL_LabelStart[SL_LABEL_COUNT] = {
   "2026.02.02 15:00",   // L1
   "2026.02.03 13:30",   // L2
   "2026.02.04 08:30",   // L3
   "2026.02.05 08:30",   // L4
   "2026.02.06 09:40",   // L5
   "2026.02.06 20:30",   // L6
   "2026.02.09 06:15",   // L7
   "2026.02.10 03:45",   // L8
   "2026.02.11 07:30",   // L9
   "2026.02.11 20:45",   // L10
   "2026.02.12 03:45",   // L11
   "2026.02.12 21:45",   // L12
   "2026.02.13 06:45",   // L13
   "2026.02.13 23:45",   // L14
   "2026.02.16 13:15",   // L15
   "2026.02.17 10:45",   // L16
   "2026.02.17 19:25",   // L17
   "2026.02.18 08:45",   // L18
   "2026.02.19 01:45",   // L19
   "2026.02.19 14:45",   // L20
   "2026.02.19 21:30",   // L21
   "2026.02.20 12:45",   // L22
   "2026.02.23 06:45",   // L23
   "2026.02.24 07:00",   // L24
   "2026.02.24 21:30",   // L25
   "2026.02.25 06:15",   // L26
   "2026.02.27 01:45"    // L27
};
string SL_LabelEnd[SL_LABEL_COUNT] = {
   "2026.02.03 01:00",   // L1
   "2026.02.04 02:00",   // L2
   "2026.02.04 16:15",   // L3
   "2026.02.05 21:15",   // L4
   "2026.02.06 13:00",   // L5
   "2026.02.06 23:45",   // L6
   "2026.02.09 16:30",   // L7
   "2026.02.11 01:15",   // L8
   "2026.02.11 11:30",   // L9
   "2026.02.11 23:45",   // L10
   "2026.02.12 18:00",   // L11
   "2026.02.13 03:00",   // L12
   "2026.02.13 15:45",   // L13
   "2026.02.16 04:15",   // L14
   "2026.02.17 01:45",   // L15
   "2026.02.17 15:30",   // L16
   "2026.02.18 03:45",   // L17
   "2026.02.18 14:45",   // L18
   "2026.02.19 07:15",   // L19
   "2026.02.19 16:45",   // L20
   "2026.02.20 07:45",   // L21
   "2026.02.20 14:45",   // L22
   "2026.02.23 16:15",   // L23
   "2026.02.24 14:15",   // L24
   "2026.02.25 02:45",   // L25
   "2026.02.25 17:45",   // L26
   "2026.02.27 15:00"    // L27
};

//--- SOURCE for the label lookup.
//---   0 = SL_LabelStart / SL_LabelEnd - the HAND LABELS from
//---       references/SIDEWAY_LABELS_FEB.md. Ground truth. Default.
//---   1 = SL_FitStart / SL_FitEnd - the same 27 ranges with per-range start and
//---       end shifts fitted to February M5 P&L.
//---
//--- MEASURED on February (M5 trend, DMONLY entries, gross):
//---   hand labels   99 trades  +1353.85
//---   fitted        85 trades  +1939.77
//---
//--- The fitted set is HINDSIGHT TWICE OVER - the ranges are hand-drawn after the
//--- fact AND the shifts are fitted to this month's P&L. 54 free parameters against
//--- 85 trades on one month. Use it to see where the headroom is, never as a result.
//--- Leave this at 0 for any run that is meant to measure detector quality.
int SL_LabelSource = 0;


string SL_FitStart[SL_LABEL_COUNT] = {
   "2026.02.02 15:00",   // F1  start +0
   "2026.02.03 13:00",   // F2  start +2
   "2026.02.04 07:00",   // F3  start +6
   "2026.02.05 09:30",   // F4  start -4
   "2026.02.06 08:15",   // F5  start +6
   "2026.02.06 21:00",   // F6  start -2
   "2026.02.09 04:15",   // F7  start +8
   "2026.02.10 03:15",   // F8  start +2
   "2026.02.11 06:30",   // F9  start +4
   "2026.02.11 19:45",   // F10 start +4
   "2026.02.12 03:15",   // F11 start +2
   "2026.02.12 21:15",   // F12 start +2
   "2026.02.13 04:45",   // F13 start +8
   "2026.02.13 21:45",   // F14 start +8
   "2026.02.16 14:15",   // F15 start -4
   "2026.02.17 10:15",   // F16 start +2
   "2026.02.17 17:30",   // F17 start +8
   "2026.02.18 07:45",   // F18 start +4
   "2026.02.19 02:45",   // F19 start -4
   "2026.02.19 13:45",   // F20 start +4
   "2026.02.19 20:30",   // F21 start +4
   "2026.02.20 10:45",   // F22 start +8
   "2026.02.23 04:45",   // F23 start +8
   "2026.02.24 05:00",   // F24 start +8
   "2026.02.24 20:00",   // F25 start +6
   "2026.02.25 04:15",   // F26 start +8
   "2026.02.26 22:45"    // F27 start +8
};
string SL_FitEnd[SL_LABEL_COUNT] = {
   "2026.02.03 01:00",   // F1  end +0
   "2026.02.04 02:00",   // F2  end +0
   "2026.02.04 16:15",   // F3  end +0
   "2026.02.05 20:15",   // F4  end -4
   "2026.02.06 12:00",   // F5  end -4
   "2026.02.06 23:45",   // F6  end +0
   "2026.02.09 17:00",   // F7  end +2
   "2026.02.11 02:15",   // F8  end +4
   "2026.02.11 11:30",   // F9  end +0
   "2026.02.12 01:15",   // F10 end +2
   "2026.02.12 19:30",   // F11 end +6
   "2026.02.13 02:30",   // F12 end -2
   "2026.02.13 15:15",   // F13 end -2
   "2026.02.16 04:15",   // F14 end +0
   "2026.02.16 21:15",   // F15 end -4
   "2026.02.17 15:30",   // F16 end +0
   "2026.02.18 02:45",   // F17 end -4
   "2026.02.18 14:15",   // F18 end -2
   "2026.02.19 06:15",   // F19 end -4
   "2026.02.19 18:15",   // F20 end +6
   "2026.02.20 06:45",   // F21 end -4
   "2026.02.20 15:15",   // F22 end +2
   "2026.02.23 16:15",   // F23 end +0
   "2026.02.24 13:45",   // F24 end -2
   "2026.02.25 02:45",   // F25 end +0
   "2026.02.25 17:45",   // F26 end +0
   "2026.02.27 14:30"    // F27 end -2
};

//+------------------------------------------------------------------+
//| Is this bar inside a hand-labelled range?                        |
//| Used only when SL_ExitMode == 4. See the hindsight warning above.|
//+------------------------------------------------------------------+
bool SL_InUserLabel(datetime t)
{
   for(int i = 0; i < SL_LABEL_COUNT; i++)
   {
      datetime t1 = StringToTime((SL_LabelSource == 1) ? SL_FitStart[i] : SL_LabelStart[i]);
      datetime t2 = StringToTime((SL_LabelSource == 1) ? SL_FitEnd[i]   : SL_LabelEnd[i]);
      if(t1 > 0 && t2 > 0 && t >= t1 && t <= t2) return true;
   }
   return false;
}


//+------------------------------------------------------------------+
//| Trade overlay: one segment per position, tagged with its P&L.    |
//| State is held here so Trade_Strategy only has to report entries  |
//| and exits.                                                       |
//+------------------------------------------------------------------+
datetime sl_tr_time  = 0;      // entry bar time, 0 = flat
double   sl_tr_price = 0.0;
string   sl_tr_dir   = "";
int      sl_tr_seq   = 0;
double   sl_tr_cum   = 0.0;    // running total, mirrors the report column

int    sl_rect_count = 0;    // label rectangles actually drawn
int    sl_win_count  = 0;    // closed trades with pnl > 0
double sl_win_sum    = 0.0;
double sl_loss_sum   = 0.0;
int    sl_r_sideways = 0;    // closes by act 7
int    sl_r_rev_dn   = 0;    // closes by act 5
int    sl_r_rev_up   = 0;    // closes by act 6

//+------------------------------------------------------------------+
//| SL_TrackAct - the ONLY place trades are drawn.                   |
//|                                                                  |
//| Driven entirely by the Trade_act the strategy just produced, so   |
//| the chart cannot drift from what the EA actually does:            |
//|    3, 4      open a position                                      |
//|    5, 6, 7   close one                                            |
//|    0         nothing                                              |
//| Call once, immediately before returning from Trade_Strategy.      |
//+------------------------------------------------------------------+
void SL_TrackAct(int act, datetime t, double px)
{
   //--- OPEN
   if(act == 3 || act == 4)
   {
      sl_tr_time  = t;
      sl_tr_price = px;
      sl_tr_dir   = (act == 3) ? "LONG" : "SHORT";
      return;
   }

   //--- CLOSE
   if(act != 5 && act != 6 && act != 7) return;   // 0 or anything else: hold
   double pnl = (sl_tr_dir == "LONG") ? (px - sl_tr_price) : (sl_tr_price - px);
   sl_tr_cum += pnl;
   if(pnl > 0.0) { sl_win_count++; sl_win_sum += pnl; }
   else          { sl_loss_sum += pnl; }
   if(act == 7)      sl_r_sideways++;
   else if(act == 5) sl_r_rev_dn++;
   else if(act == 6) sl_r_rev_up++;
   sl_tr_seq++;
   if(!SL_DrawTrades || sl_tr_time == 0) { sl_tr_time = 0; return; }

   string reason = (act == 5) ? "REVERSAL_DN" : (act == 6) ? "REVERSAL_UP" : "SIDEWAYS";
   color  col    = (pnl > 0.0) ? SL_WinColor : SL_LossColor;
   string base   = "SLTR_" + IntegerToString(sl_tr_seq);

   if(ObjectCreate(0, base, OBJ_TREND, 0, sl_tr_time, sl_tr_price, t, px))
   {
      ObjectSetInteger(0, base, OBJPROP_COLOR,      col);
      ObjectSetInteger(0, base, OBJPROP_WIDTH,      SL_TradeWidth);
      ObjectSetInteger(0, base, OBJPROP_RAY_RIGHT,  false);
      ObjectSetInteger(0, base, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, base, OBJPROP_BACK,       false);
      ObjectSetString (0, base, OBJPROP_TOOLTIP,
                       "#" + IntegerToString(sl_tr_seq) + " " + sl_tr_dir +
                       "  " + TimeToString(sl_tr_time, TIME_DATE|TIME_MINUTES) +
                       " -> " + TimeToString(t, TIME_DATE|TIME_MINUTES) +
                       "  act " + IntegerToString(act) + " " + reason +
                       "  P&L " + DoubleToString(pnl, 2) +
                       "  cum " + DoubleToString(sl_tr_cum, 2));
   }

   string tag = base + "_T";
   if(ObjectCreate(0, tag, OBJ_TEXT, 0, t, px))
   {
      ObjectSetString (0, tag, OBJPROP_TEXT,
                       DoubleToString(pnl, 2) + " (" + DoubleToString(sl_tr_cum, 2) + ")");
      ObjectSetInteger(0, tag, OBJPROP_COLOR,      col);
      ObjectSetInteger(0, tag, OBJPROP_FONTSIZE,   SL_TradeFont);
      ObjectSetInteger(0, tag, OBJPROP_ANCHOR,
                       (sl_tr_dir == "LONG") ? ANCHOR_LOWER : ANCHOR_UPPER);
      ObjectSetInteger(0, tag, OBJPROP_SELECTABLE, false);
   }

   sl_tr_time = 0;
}

//+------------------------------------------------------------------+
//| Draw the labelled ranges. Call ONCE (OnInit, or guarded by a     |
//| static flag) - not per bar.                                      |
//+------------------------------------------------------------------+
void SL_DrawUserLabelRanges()
{
   if(!SL_DrawUserLabels) return;

   for(int i = 0; i < SL_LABEL_COUNT; i++)
   {
      datetime t1 = StringToTime((SL_LabelSource == 1) ? SL_FitStart[i] : SL_LabelStart[i]);
      datetime t2 = StringToTime((SL_LabelSource == 1) ? SL_FitEnd[i]   : SL_LabelEnd[i]);
      if(t1 <= 0 || t2 <= 0 || t2 <= t1) continue;

      //--- Wait until the range has FULLY formed. Before that iBarShift returns the
      //--- LATEST bar for a future timestamp, so b1 == b2 == 0, the high/low scan
      //--- covers one bar, and the rectangle is built from the wrong bars. ObjectFind
      //--- then locks that bad geometry in permanently.
      if(iTime(_Symbol, PERIOD_M15, 0) <= t2) continue;

      string name = "SLLBL_" + IntegerToString(i + 1);
      if(ObjectFind(0, name) >= 0) continue;

      int b1 = iBarShift(_Symbol, PERIOD_M15, t2, false);   // newer = smaller shift
      int b2 = iBarShift(_Symbol, PERIOD_M15, t1, false);   // older = larger shift
      if(b1 < 0 || b2 < 0 || b2 < b1) continue;

      //--- scan bars directly. iHighest/iLowest are ambiguous here because
      //--- mql4compat.mqh declares int-typed overloads alongside the MQL5
      //--- built-ins, so the compiler cannot resolve the call.
      double hi = 0.0, lo = 0.0;
      for(int b = b1; b <= b2; b++)
      {
         double h = iHigh(_Symbol, PERIOD_M15, b);
         double l = iLow (_Symbol, PERIOD_M15, b);
         if(h <= 0.0 || l <= 0.0) continue;
         if(hi == 0.0 || h > hi) hi = h;
         if(lo == 0.0 || l < lo) lo = l;
      }
      if(hi <= 0.0 || lo <= 0.0 || hi <= lo) continue;

      if(!ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, lo, t2, hi)) continue;
      ObjectSetInteger(0, name, OBJPROP_COLOR,      SL_LabelColor);
      ObjectSetInteger(0, name, OBJPROP_FILL,       SL_LabelFill);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 5);
      ObjectSetInteger(0, name, OBJPROP_BACK,       true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetString (0, name, OBJPROP_TOOLTIP,
                       ((SL_LabelSource == 1) ? "FITTED F" : "SIDEWAY L") +
                       "LABEL " + IntegerToString(i + 1) + "  " +
                       SL_LabelStart[i] + " -> " + SL_LabelEnd[i]);
      sl_rect_count++;
   }
}

//+------------------------------------------------------------------+
//| LADDER LABEL OVERLAY + DUAL VIRTUAL SIMULATION                   |
//|                                                                  |
//| Two independent things are drawn and scored side by side:        |
//|   USER  - the hand labels from SIDEWAY_LABELS_FEB.md             |
//|           pink rectangles spanning the range high/low            |
//|   LADD  - what the ladder detects (SL_state >= 2)                |
//|           aqua marks on top of the M15 midline                   |
//|                                                                  |
//| Both run a VIRTUAL DMONLY simulation in parallel - neither one   |
//| places orders. That is what SL_ExitMode and the real             |
//| Trade_Strategy are for. These two exist purely so one backtest    |
//| shows how far the ladder is from the labels, in bars AND in P&L.  |
//|                                                                  |
//| MEASURED in Python on February (for comparison):                 |
//|   USER labels    858 bars, 27 ranges, 58 trades, +415.36         |
//|   ladder L1=1 L2=0 brk=2   857 bars, 57 ranges, 79 trades, -131  |
//|   ladder + M30 latch       1072 bars, 60 ranges, 68 trades, +57  |
//+------------------------------------------------------------------+
bool   SL_DrawLadderLabels = true;      // aqua marks where the ladder says sideway
color  SL_LadderColor     = MistyRose;
int    SL_LadderFont      = 7;

//--- Virtual trade labels. Same OpenB / CloseB / OpenS / CloseS wording the EA
//--- writes into TRADE_comment, so the two virtual runs read like real ones.
//---   PINK  = the USER-label run
//---   WHITE = the ladder run
//--- One toggle per virtual run, so either can be shown alone.
//---   [0] = USER labels   [1] = ladder
bool   SL_DrawVirtual[2] = {true, true};
color  SL_UserTradeColor    = Magenta;   // yellow - user labels. NOT magenta: the
                                                // label rectangles are magenta, so a
                                                // magenta trade line vanishes on top of them.
color  SL_LaddTradeColor    = clrDeepSkyBlue;  // blue - ladder. NOT white: the EA
                                               // draws its own OpenB/CloseB in white.
int    SL_VTradeFont        = 8;
int    SL_VTradeWidth       = 3;    // virtual trade line thickness

//--- virtual sim state: [0] = USER labels, [1] = ladder
datetime sv_time[2]  = {0, 0};
double   sv_price[2] = {0.0, 0.0};
string   sv_dir[2]   = {"", ""};
int      sv_trades[2]  = {0, 0};
int      sv_wins[2]    = {0, 0};
double   sv_pnl[2]     = {0.0, 0.0};
int      sv_bars[2]    = {0, 0};        // bars flagged sideway
int      sv_ranges[2]  = {0, 0};        // contiguous sideway blocks
bool     sv_prev_sw[2] = {false, false};
int      sv_agree      = 0;             // bars where both agree sideway
int      sv_user_only  = 0;
int      sv_ladd_only  = 0;
int      sv_scored     = 0;

//--- last virtual event per source, folded into the [SWCMP] line instead of
//--- emitting a separate stream. "" = nothing happened on this bar.
string   sv_evt[2]     = {"", ""};

//+------------------------------------------------------------------+
//| S30 CHAIN WAIVER  +  M30 LATCH                      (v38.16)     |
//|                                                                  |
//| Both measured against references/SIDEWAY_LABELS_FEB.md            |
//| (27 ranges, 858 bars, 58 trades, +415.36 = the hindsight ceiling).|
//|                                                                  |
//| 1. SL_S30WaivesChain                                              |
//|    Level 2 normally needs prev >= 1 - the M15 chain must already  |
//|    be running. With this on, S30 alone waives that requirement.   |
//|    A30 and ev30 STILL apply; only the chain is skipped.           |
//|    Not the same as S30 setting state 2 outright:                  |
//|      S30 overrides everything  -> helped 69/72 pairs, best  +37   |
//|      S30 waives the chain only -> helped 31/72 pairs, best +202   |
//|    The second helps in fewer places but far more where it does.   |
//|                                                                  |
//| 2. SL_UseM30Latch                                                 |
//|    A range is a PERIOD, not a per-bar property. Without a latch   |
//|    the detector re-decides each bar and one labelled range comes  |
//|    out as several fragments - 27 labelled became 57-60 detected.  |
//|    With it, detection ENGAGES the state and only a close outside  |
//|    the M30 band RELEASES it.                                      |
//|                                                                  |
//| MEASURED, best cell of each (February):                           |
//|   plain                        -250.66   54 ranges, 67 trades     |
//|   + latch                       +57.06   60 ranges, 68 trades     |
//|   + latch + S30 waiver         +201.83   56 ranges, 66 trades     |
//|                                          at L1=1 L2=1 brk=0       |
//|                                                                  |
//| CAUTION: +201.83 is the best of 216 configurations tested on the  |
//| SAME month the labels were drawn from. Its F1 is 71.9 vs 73.9 for |
//| the latch-only cell - WORSE detection, better P&L. That pattern   |
//| is what overfitting looks like. The latch itself is a structural  |
//| fix and improved things broadly; the specific L1=1 L2=1 brk=0     |
//| cell is a candidate, not a validated edge, until it runs on a     |
//| second month labelled BEFORE the run.                             |
//|                                                                  |
//| A latch has MEMORY: a false engage costs the whole run until the  |
//| next breakout, not one bar. It amplifies good and bad detections. |
//+------------------------------------------------------------------+
bool   SL_S30WaivesChain = true;   // S30 skips the prev >= 1 requirement
bool   SL_UseM30Latch    = true;   // hold sideway until price leaves the M30 band

//--- latch state. true = a range is currently open.
bool   sl_latched = false;

//+------------------------------------------------------------------+
//| LADDER RANGE RECTANGLES                                          |
//|                                                                  |
//| The ladder equivalent of SL_DrawUserLabelRanges. A ladder range   |
//| is a run of consecutive SL_state >= 2 bars; when the run ends,    |
//| the whole span is drawn as one rectangle over the high/low the    |
//| candles actually traded inside it.                                |
//|                                                                  |
//| Put side by side with the pink hand-label rectangles, the two     |
//| block sets show over- and under-detection as GEOMETRY rather      |
//| than as a trade count: 27 labelled ranges have been coming out    |
//| as 50-60 ladder ranges, and that fragmentation is the single      |
//| largest difference between them.                                  |
//|                                                                  |
//| Drawn only when a range CLOSES, so the geometry is final - the    |
//| same reason SL_DrawUserLabelRanges waits for a range to form      |
//| before drawing it.                                                |
//+------------------------------------------------------------------+
bool     SL_DrawLadderRanges = true;              // ladder ranges as rectangles
// color    SL_LadderRangeColor = clrDarkSlateGray;
color    SL_LadderRangeColor = MistyRose;
bool     SL_LadderRangeFill  = false;
int      SL_LadderRangeFont  = 8;

//--- open ladder range: 0 = none currently open
datetime sl_lr_start = 0;
int      sl_lr_seq   = 0;

//--- ladder state history: [LA]=current, ages toward [LA_4]
int SL_state[5];

//+------------------------------------------------------------------+
//| stage counts as a sideway-ish stage                              |
//+------------------------------------------------------------------+
bool SL_StageOK(int st)
{  return (st == 513 || st == 523 || (st >= 400 && st <= 499)); }

//+------------------------------------------------------------------+
//| One step of a virtual DMONLY run. Places NO orders.              |
//|   which : 0 = USER labels, 1 = ladder                             |
//|   sw    : is this bar sideway according to that source            |
//| Same rules as Trade_Strategy: sideway exits all and blocks entry, |
//| opposite dm exits, entry only when flat, close-only.              |
//+------------------------------------------------------------------+
void SL_VirtualStep(int which, bool sw, double dm, datetime t, double px)
{
   //--- range accounting
   if(sw)
   {
      sv_bars[which]++;
      if(!sv_prev_sw[which]) sv_ranges[which]++;
   }
   sv_prev_sw[which] = sw;

   bool dm1_up   = (dm == 1.0 || dm == 5.0);
   bool dm1_down = (dm == 2.0 || dm == 4.0);
   bool inpos   = (sv_time[which] != 0);
   bool inLong  = (inpos && sv_dir[which] == "LONG");
   bool inShort = (inpos && sv_dir[which] == "SHORT");

   //--- Decide Trade_act exactly as Trade_Strategy does, so the virtual runs
   //--- follow the same rules the real strategy would.
   //---   7 exit_all        3 no_exit_entry_buy   4 no_exit_entry_sell
   //---   5 exit_buy        6 exit_sell           0 hold
   int act = 0;
   if(sw)
   {
      if(inpos) act = 7;                       // sideway: close everything
   }
   else if(inLong  && dm1_down) act = 5;
   else if(inShort && dm1_up)   act = 6;
   else if(!inpos)
   {
      if(dm1_up)        act = 3;
      else if(dm1_down) act = 4;
   }
   if(act == 0) return;

   //--- Build the comment the same way the EA does for each act, so the chart
   //--- label reads like a real trade line: CloseB, OpenS, CloseS-OpenB, ...
   string cmt = "";

   //--- closes
   if(act == 7 || act == 5 || act == 6)
   {
      if(inLong  && (act == 7 || act == 5)) cmt = "CloseB";
      if(inShort && (act == 7 || act == 6)) cmt = "CloseS";

      double pnl = inLong ? (px - sv_price[which]) : (sv_price[which] - px);
      sv_pnl[which] += pnl;
      sv_trades[which]++;
      if(pnl > 0.0) sv_wins[which]++;

      sv_evt[which] = cmt + "#" + IntegerToString(sv_trades[which]) +
                      " pnl:" + DoubleToString(pnl, 2) +
                      " cum:" + DoubleToString(sv_pnl[which], 2) +
                      " w:" + IntegerToString(sv_wins[which]) +
                      "/" + IntegerToString(sv_trades[which]);

      if(SL_DrawVirtual[which])
      {
         color col = (which == 0) ? SL_UserTradeColor : SL_LaddTradeColor;
         string tag = (which == 0) ? "SVU_" : "SVL_";
         string nm  = tag + IntegerToString(sv_trades[which]) + "_C";
         if(ObjectFind(0, nm) < 0 && ObjectCreate(0, nm, OBJ_TEXT, 0, t, px))
         {
            ObjectSetString (0, nm, OBJPROP_TEXT,
                             cmt + " " + DoubleToString(pnl, 2) +
                             " (" + DoubleToString(sv_pnl[which], 2) + ")");
            ObjectSetInteger(0, nm, OBJPROP_COLOR,      col);
            ObjectSetInteger(0, nm, OBJPROP_FONTSIZE,   SL_VTradeFont);
            ObjectSetInteger(0, nm, OBJPROP_ANCHOR,
                             inLong ? ANCHOR_UPPER : ANCHOR_LOWER);
            ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
         }
         //--- the segment from entry to exit
         string sn = tag + IntegerToString(sv_trades[which]) + "_L";
         if(ObjectFind(0, sn) < 0 &&
            ObjectCreate(0, sn, OBJ_TREND, 0, sv_time[which], sv_price[which], t, px))
         {
            ObjectSetInteger(0, sn, OBJPROP_COLOR,      col);
            ObjectSetInteger(0, sn, OBJPROP_WIDTH,      SL_VTradeWidth);
            ObjectSetInteger(0, sn, OBJPROP_RAY_RIGHT,  false);
            ObjectSetInteger(0, sn, OBJPROP_SELECTABLE, false);
            ObjectSetString (0, sn, OBJPROP_TOOLTIP,
                             ((which == 0) ? "USER #" : "LADDER #") +
                             IntegerToString(sv_trades[which]) + " " + sv_dir[which] +
                             " act:" + IntegerToString(act) +
                             " pnl:" + DoubleToString(pnl, 2));
         }
      }

      sv_time[which] = 0;
      return;                                  // close-only: no re-entry this bar
   }

   //--- opens
   if(act == 3 || act == 4)
   {
      sv_time[which]  = t;
      sv_price[which] = px;
      sv_dir[which]   = (act == 3) ? "LONG" : "SHORT";
      cmt             = (act == 3) ? "OpenB" : "OpenS";

      sv_evt[which] = cmt + "#" + IntegerToString(sv_trades[which] + 1) +
                      " @" + DoubleToString(px, 2) +
                      " cum:" + DoubleToString(sv_pnl[which], 2);

      if(SL_DrawVirtual[which])
      {
         color col = (which == 0) ? SL_UserTradeColor : SL_LaddTradeColor;
         string tag = (which == 0) ? "SVU_" : "SVL_";
         string nm  = tag + IntegerToString(sv_trades[which] + 1) + "_O";
         if(ObjectFind(0, nm) < 0 && ObjectCreate(0, nm, OBJ_TEXT, 0, t, px))
         {
            ObjectSetString (0, nm, OBJPROP_TEXT,       cmt);
            ObjectSetInteger(0, nm, OBJPROP_COLOR,      col);
            ObjectSetInteger(0, nm, OBJPROP_FONTSIZE,   SL_VTradeFont);
            ObjectSetInteger(0, nm, OBJPROP_ANCHOR,
                             (act == 3) ? ANCHOR_LOWER : ANCHOR_UPPER);
            ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Mark a ladder-detected sideway bar on top of the M15 midline.    |
//+------------------------------------------------------------------+
void SL_DrawLadderLabel(datetime t, double mid)
{
   if(!SL_DrawLadderLabels || mid <= 0.0 || t <= 0) return;

   string name = "SLLAD_" + IntegerToString((int)t);
   if(ObjectFind(0, name) >= 0) return;

   if(!ObjectCreate(0, name, OBJ_TEXT, 0, t, mid)) return;
   ObjectSetString (0, name, OBJPROP_TEXT,       "*");
   ObjectSetInteger(0, name, OBJPROP_COLOR,      SL_LadderColor);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE,   SL_LadderFont);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR,     ANCHOR_LOWER);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
}

//+------------------------------------------------------------------+
//| Close the currently open ladder range and draw it.               |
//| t_end = the last bar that was still sideway.                     |
//+------------------------------------------------------------------+
void SL_CloseLadderRange(datetime t_end)
{
   if(sl_lr_start == 0) return;
   if(!SL_DrawLadderRanges || t_end <= sl_lr_start) { sl_lr_start = 0; return; }

   int b1 = iBarShift(_Symbol, PERIOD_M15, t_end,       false);   // newer, smaller shift
   int b2 = iBarShift(_Symbol, PERIOD_M15, sl_lr_start, false);   // older, larger shift
   if(b1 < 0 || b2 < 0 || b2 < b1) { sl_lr_start = 0; return; }

   //--- scan bars directly. iHighest/iLowest are ambiguous here because
   //--- mql4compat.mqh declares int-typed overloads next to the MQL5 built-ins.
   double hi = 0.0, lo = 0.0;
   for(int b = b1; b <= b2; b++)
   {
      double h = iHigh(_Symbol, PERIOD_M15, b);
      double l = iLow (_Symbol, PERIOD_M15, b);
      if(h <= 0.0 || l <= 0.0) continue;
      if(hi == 0.0 || h > hi) hi = h;
      if(lo == 0.0 || l < lo) lo = l;
   }
   if(hi <= 0.0 || lo <= 0.0 || hi <= lo) { sl_lr_start = 0; return; }

   sl_lr_seq++;
   string name = "SLLR_" + IntegerToString(sl_lr_seq);
   if(ObjectFind(0, name) < 0 &&
      ObjectCreate(0, name, OBJ_RECTANGLE, 0, sl_lr_start, lo, t_end, hi))
   {
      ObjectSetInteger(0, name, OBJPROP_COLOR,      SL_LadderRangeColor);
      ObjectSetInteger(0, name, OBJPROP_FILL,       SL_LadderRangeFill);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 5);
      ObjectSetInteger(0, name, OBJPROP_BACK,       true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetString (0, name, OBJPROP_TOOLTIP,
                       "LADDER RANGE #" + IntegerToString(sl_lr_seq) + "  " +
                       TimeToString(sl_lr_start, TIME_DATE|TIME_MINUTES) + " -> " +
                       TimeToString(t_end, TIME_DATE|TIME_MINUTES) +
                       "  bars " + IntegerToString(b2 - b1 + 1) +
                       "  range " + DoubleToString(lo, 2) + " - " + DoubleToString(hi, 2));

      string tag = name + "_T";
      if(ObjectCreate(0, tag, OBJ_TEXT, 0, sl_lr_start, lo))
      {
         ObjectSetString (0, tag, OBJPROP_TEXT,       "LR" + IntegerToString(sl_lr_seq));
         ObjectSetInteger(0, tag, OBJPROP_COLOR,      SL_LadderRangeColor);
         ObjectSetInteger(0, tag, OBJPROP_FONTSIZE,   SL_LadderRangeFont);
         ObjectSetInteger(0, tag, OBJPROP_ANCHOR,     ANCHOR_UPPER);
         ObjectSetInteger(0, tag, OBJPROP_SELECTABLE, false);
      }
   }
   sl_lr_start = 0;
}

//+------------------------------------------------------------------+
//| Draw one tag label on a timeframe's own midline, at that          |
//| timeframe's own bar time. Called once per level.                  |
//| SL_Update runs per M15 bar, so slower levels are reached several  |
//| times inside one of their own bars; ObjectFind lets only the      |
//| first create the label. That is harmless - the tags are built     |
//| from that timeframe's BB_datas, which do not change within its    |
//| own bar, so every call computes the same string.                  |
//+------------------------------------------------------------------+
void SL_DrawTagLabel(string prefix, string tags, double mid,
                     ENUM_TIMEFRAMES tf, color col)
{
   datetime t = iTime(_Symbol, tf, 0);
   if(mid <= 0.0 || t <= 0) return;

   double y = mid + SL_TagOffsetPts * _Point;   // lift clear of the midline
   // double y = mid + SL_TagOffsetPts;   // lift clear of the midline

   string name = prefix + IntegerToString((int)t);
   if(ObjectFind(0, name) >= 0) return;
   if(!ObjectCreate(0, name, OBJ_TEXT, 0, t, y)) return;

   ObjectSetString (0, name, OBJPROP_TEXT,       "{" + (tags == "" ? "-" : tags) + "}");
   ObjectSetInteger(0, name, OBJPROP_COLOR,      col);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE,   SL_FontSize);
   ObjectSetDouble (0, name, OBJPROP_ANGLE,      SL_Angle);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR,     ANCHOR_LOWER);
   ObjectSetInteger(0, name, OBJPROP_BACK,       false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
}

//+------------------------------------------------------------------+
//| Compute the ladder for the current bar. Call ONCE per M15 bar,   |
//| AFTER BBDatas_Midline_Cluster has updated BB_midline_Cluster.    |
//+------------------------------------------------------------------+
void SL_Update(BB_MTF_Impact_struct &BBTFImpact,
               BB_MTF_Data_struct   &BB_datas[])
{
   //--- Self-guard: this MUST run exactly once per M15 bar. The state history below
   //--- is indexed in M15 bars, so running per M5 tick would age `prev` three times
   //--- too fast and break every `prev >= 1` chain check, the latch, and the range
   //--- tracker. Guarding here means the EA can call it from anywhere safely.
   static datetime sl_lastM15 = 0;
   datetime m15now = iTime(_Symbol, PERIOD_M15, 0);
   if(m15now == sl_lastM15) return;
   sl_lastM15 = m15now;

   //--- age the history
   SL_state[LA_4] = SL_state[LA_3];
   SL_state[LA_3] = SL_state[LA_2];
   SL_state[LA_2] = SL_state[LA_1];
   SL_state[LA_1] = SL_state[LA];
   SL_state[LA]   = 0;

   int prev = SL_state[LA_1];

   //--- cluster distances, current and two bars back
   //--- diffMid_Trend CODES (1..5). Distinct from the dm* DISTANCES above:
   //--- the C and D tags read codes, the M and B tags read distances.
   double dmt0  = BB_datas[0].BB_diffMid_Trend[LA];
   double dmt1  = BB_datas[1].BB_diffMid_Trend[LA];
   double dmt1a = BB_datas[1].BB_diffMid_Trend[LA_1];
   double dmt1b = BB_datas[1].BB_diffMid_Trend[LA_2];
   double dmt2  = BB_datas[2].BB_diffMid_Trend[LA];
   double dmt2a = BB_datas[2].BB_diffMid_Trend[LA_1];
   double dmt2b = BB_datas[2].BB_diffMid_Trend[LA_2];
   double dmt3  = BB_datas[3].BB_diffMid_Trend[LA];
   double dmt3a = BB_datas[3].BB_diffMid_Trend[LA_1];
   double dmt3b = BB_datas[3].BB_diffMid_Trend[LA_2];
   double dmt4  = BB_datas[4].BB_diffMid_Trend[LA];
   double dmt4a = BB_datas[4].BB_diffMid_Trend[LA_1];
   double dmt4b = BB_datas[4].BB_diffMid_Trend[LA_2];

   double c0  = BBTFImpact.BB_midline_Cluster[0][LA];    // M5 + M15
   double c0a = BBTFImpact.BB_midline_Cluster[0][LA_1];
   double c0b = BBTFImpact.BB_midline_Cluster[0][LA_2];
   double c1  = BBTFImpact.BB_midline_Cluster[1][LA];    // M15 + M30
   double c1a = BBTFImpact.BB_midline_Cluster[1][LA_1];
   double c1b = BBTFImpact.BB_midline_Cluster[1][LA_2];
   double c2  = BBTFImpact.BB_midline_Cluster[2][LA];
   double c2a = BBTFImpact.BB_midline_Cluster[2][LA_1];
   double c2b = BBTFImpact.BB_midline_Cluster[2][LA_2];
   double c3  = BBTFImpact.BB_midline_Cluster[3][LA];
   double c3a = BBTFImpact.BB_midline_Cluster[3][LA_1];
   double c3b = BBTFImpact.BB_midline_Cluster[3][LA_2];

   double dm1  = MathAbs(BB_datas[1].BB_diffMid[LA]);
   double dm1a = MathAbs(BB_datas[1].BB_diffMid[LA_1]);
   double dm1b = MathAbs(BB_datas[1].BB_diffMid[LA_2]);
   double dm2  = MathAbs(BB_datas[2].BB_diffMid[LA]);
   double dm2a = MathAbs(BB_datas[2].BB_diffMid[LA_1]);
   double dm2b = MathAbs(BB_datas[2].BB_diffMid[LA_2]);
   double dm3  = MathAbs(BB_datas[3].BB_diffMid[LA]);
   double dm3a = MathAbs(BB_datas[3].BB_diffMid[LA_1]);
   double dm3b = MathAbs(BB_datas[3].BB_diffMid[LA_2]);
   double dm4  = MathAbs(BB_datas[4].BB_diffMid[LA]);
   double dm4a = MathAbs(BB_datas[4].BB_diffMid[LA_1]);
   double dm4b = MathAbs(BB_datas[4].BB_diffMid[LA_2]);

   //--- LEVEL 1 predicates, named individually (lift measured alone)
   bool A15 = ((c0 < c0a && c0a < c0b) || (c0 < CL_NEAR_M15 && c0a < CL_NEAR_M15));  // +4.5
   bool S15 = SL_StageOK((int)BB_datas[1].BBW_stage[LA]);                    // +3.3
   bool C15 = (dm1 < SL_diffmid_m15 && dm1a < SL_diffmid_m15);               // +5.3
   bool D15 = (dm1 < dm1a && dm1a < dm1b);                                   // no use
   bool W15 = (BB_datas[1].BB_diffBBW[LA]   < SL_diffbbw_m15
            && BB_datas[1].BB_diffBBW[LA_1] < SL_diffbbw_m15);  

   //--- LEVEL-1 DIAGNOSTIC TAGS - reporting only, no effect on any decision.
   string l1tags = "";
   if(SL_DrawL1Tags)
   {
      if(c0 < CL_NEAR_M15 && c0a < CL_NEAR_M15)           l1tags += "A";
      if(S15)                                             l1tags += "S";
      if(dm1 < dm1a && dm1a < dm1b)                       l1tags += "B";
      if(dmt1 >= 3.0 && dmt1a >= 3.0 &&
         (dmt1 == 3.0 || dmt1a == 3.0 || dmt1b == 3.0))   l1tags += "C";
      if(W15)                                             l1tags += "W";
      if(dm1 < SL_diffmid_m15 && dm1a < SL_diffmid_m15)   l1tags += "M";
      if(((dmt0 == 1.0 || dmt0 == 5.0) && (dmt1 == 2.0 || dmt1 == 4.0)) ||
         ((dmt0 == 2.0 || dmt0 == 4.0) && (dmt1 == 1.0 || dmt1 == 5.0)) ||
         (dmt0 == 3.0 || dmt1 == 3.0))                    l1tags += "D";
   }

   bool lvl1 = false;
   if(SL_L1Mode == 0)      lvl1 = (A15 && (S15 || C15));
   else if(SL_L1Mode == 1) lvl1 = (A15 && C15);                              // current use
   else if(SL_L1Mode == 2) lvl1 = (A15 && S15);
   else if(SL_L1Mode == 3) lvl1 = (A15 && S15 && C15);
   else if(SL_L1Mode == 4) lvl1 = (A15 && (S15 || C15) && (D15 || C15));
   else if(SL_L1Mode == 5) lvl1 = (A15 && (S15 || W15) && (D15 || C15));
   else if(SL_L1Mode == 6) lvl1 = (A15 && (S15 || W15 || D15 || C15));
   else if(SL_L1Mode == 7) lvl1 = (A15 && (S15 || C15 || W15));

   if(lvl1) SL_state[LA] = 1;

   //--- LEVEL 2 predicates, named individually
   bool A30 = ((c1 < c1a && c1a < c1b) || (c1 < CL_NEAR_M15 && c1a < CL_NEAR_M15));  // +5.4
   bool S30 = SL_StageOK((int)BB_datas[2].BBW_stage[LA]);                    // +4.1
   bool C30 = (dm2 < SL_diffmid_m30 && dm2a < SL_diffmid_m30);               // +10.9
   bool D30 = (dm2 < dm2a && dm2a < dm2b);                                   // no use
   bool W30 = (BB_datas[2].BB_diffBBW[LA]   < SL_diffbbw_m30
            && BB_datas[2].BB_diffBBW[LA_1] < SL_diffbbw_m30);               // +4.4

   //--- LEVEL-2 (M30) DIAGNOSTIC TAGS - reporting only, no effect on any decision.
   string l2tags = "";
   if(SL_DrawL2Tags)
   {
      if(c1 < CL_NEAR_M30 && c1a < CL_NEAR_M30)           l2tags += "A";
      if(S30)                                             l2tags += "S";
      if(dm2 < dm2a && dm2a < dm2b)                       l2tags += "B";
      if(dmt2 >= 3.0 && dmt2a >= 3.0 &&
         (dmt2 == 3.0 || dmt2a == 3.0 || dmt2b == 3.0))   l2tags += "C";
      if(W30)                                             l2tags += "W";
      if(dm2 < SL_diffmid_m30 && dm2a < SL_diffmid_m30)   l2tags += "M";
      if(((dmt1 == 1.0 || dmt1 == 5.0) && (dmt2 == 2.0 || dmt2 == 4.0)) ||
         ((dmt1 == 2.0 || dmt1 == 4.0) && (dmt2 == 1.0 || dmt2 == 5.0)) ||
         (dmt1 == 3.0 || dmt2 == 3.0))                    l2tags += "D";
   }

   //--- LEVEL-3 (H1) and LEVEL-4 (H4) tags. No B/D contraction tag on these two -
   //--- only stage, the threshold shape, and band-width contraction.
   bool SH1 = SL_StageOK((int)BB_datas[3].BBW_stage[LA]);
   bool WH1 = (BB_datas[3].BB_diffBBW[LA]   < SL_diffbbw_H1
            && BB_datas[3].BB_diffBBW[LA_1] < SL_diffbbw_H1);
   string l3tags = "";
   if(SL_DrawL3Tags)
   {
      if(c2 < CL_NEAR_H1 && c2a < CL_NEAR_H1)             l3tags += "A";
      if(SH1)                                             l3tags += "S";
      if(dmt3 >= 3.0 && dmt3a >= 3.0 &&
         (dmt3 == 3.0 || dmt3a == 3.0 || dmt3b == 3.0))   l3tags += "C";
      if(dm3 < SL_diffmid_H1 && dm3a < SL_diffmid_H1)     l3tags += "M";
      if(WH1)                                             l3tags += "W";
      //--- NOTE: the spec compared dmt3 with itself here, which is always false.
      //--- Read as M30 vs H1, matching the L1D / L2D pattern.
      if(((dmt2 == 1.0 || dmt2 == 5.0) && (dmt3 == 2.0 || dmt3 == 4.0)) ||
         ((dmt2 == 2.0 || dmt2 == 4.0) && (dmt3 == 1.0 || dmt3 == 5.0)) ||
         (dmt2 == 3.0 || dmt3 == 3.0))                    l3tags += "D";
   }

   bool SH4 = SL_StageOK((int)BB_datas[4].BBW_stage[LA]);
   bool WH4 = (BB_datas[4].BB_diffBBW[LA]   < SL_diffbbw_H4
            && BB_datas[4].BB_diffBBW[LA_1] < SL_diffbbw_H4);
   string l4tags = "";
   if(SL_DrawL4Tags)
   {
      if(c3 < CL_NEAR_H4 && c3a < CL_NEAR_H4)             l4tags += "A";
      if(SH4)                                             l4tags += "S";
      if(dmt4 >= 3.0 && dmt4a >= 3.0 &&
         (dmt4 == 3.0 || dmt4a == 3.0 || dmt4b == 3.0))   l4tags += "C";
      if(dm4 < SL_diffmid_H4 && dm4a < SL_diffmid_H4)     l4tags += "M";
      if(WH4)                                             l4tags += "W";
   }

   bool ev30 = false;
   if(SL_L2Mode == 0)      ev30 = (S30 || C30 || W30);                       // current use 
   else if(SL_L2Mode == 1) ev30 = (S30 || C30);
   else if(SL_L2Mode == 2) ev30 = C30;
   else if(SL_L2Mode == 3) ev30 = (A30 && (S30 || C30));
   else if(SL_L2Mode == 4) ev30 = (A30 && (S30 || C30 || W30));

   //--- S30 can waive the prev >= 1 chain. A30 and ev30 still apply.
   bool chain_ok = (prev >= 1);
   if(SL_S30WaivesChain && S30) chain_ok = true;

   if(chain_ok && A30 && ev30) SL_state[LA] = 2;

   //--- BREAKOUT CANCELS the sideway state (M15 band, index 1)
   bool brk = false;
   if(SL_BreakoutMode > 0)
   {
      // bool raw = false;
      // bool raw1 = false;
      // if(SL_state[LA] == 1)
      // {
      //    raw = (BB_datas[1].BB_diffMid[LA] < 3 || BB_datas[1].BBW_stage[LA] == 511 || BB_datas[1].BBW_stage[LA] == 521);
      // }
      // else if(SL_state[LA] == 2)
      // {
      //    raw1 = (BB_datas[2].BB_diffMid[LA] < 3 || BB_datas[2].BBW_stage[LA] == 511 || BB_datas[2].BBW_stage[LA] == 521);
      // }
      double close_now  = iClose(_Symbol, PERIOD_M5, 0);
      double close_prev = iClose(_Symbol, PERIOD_M5, 3);   // 3 M5 bars = 1 M15 bar back

      bool raw  = (close_now  > BB_datas[1].BBUppLV[LA]
                || close_now  < BB_datas[1].BBLowLV[LA]);
      bool raw1 = (close_prev > BB_datas[1].BBUppLV[LA_1]
                || close_prev < BB_datas[1].BBLowLV[LA_1]);

      //--- M30 band, same two-bar shape as raw / raw1 on M15
      bool raw30  = (close_now  > BB_datas[2].BBUppLV[LA]
                  || close_now  < BB_datas[2].BBLowLV[LA]);
      bool raw30p = (close_prev > BB_datas[2].BBUppLV[LA_1]
                  || close_prev < BB_datas[2].BBLowLV[LA_1]);

      //--- Did the OTHER timeframe break out within the last SL_BrkLookback bars?
      //--- Rolling history, one slot per M15 bar. SL_Update is guarded to run once
      //--- per M15 bar, so these advance in step with the ladder's own history.
      static bool h15[8], h30[8];
      static int  hn = 0;
      bool prior15 = false, prior30 = false;
      int look = (SL_BrkLookback < 1) ? 1 : (SL_BrkLookback > 8 ? 8 : SL_BrkLookback);
      for(int k = 0; k < look && k < hn; k++)
      {
         int idx = (hn - 1 - k) % 8;
         if(h15[idx]) prior15 = true;
         if(h30[idx]) prior30 = true;
      }

      if(SL_BreakoutMode == 1)      brk = raw;
      else if(SL_BreakoutMode == 2) brk = (raw && raw1);
      else if(SL_BreakoutMode == 3) brk = (raw && !C15);                   // current use
      else if(SL_BreakoutMode == 4) brk = (raw && !C15 && !W15);
      else if(SL_BreakoutMode == 5) brk = raw30;                           // M30 alone
      else if(SL_BreakoutMode == 6) brk = (raw || raw30);                  // either band
      else if(SL_BreakoutMode == 7) brk = (raw && raw30);                  // both bands
      else if(SL_BreakoutMode == 8) brk = (raw30 && raw30p);               // M30 confirmed
      else if(SL_BreakoutMode == 9) brk = (prior15 && raw30);              // M15 then M30

      //--- record this bar for the next call's lookback
      h15[hn % 8] = raw;
      h30[hn % 8] = raw30;
      hn++;

      if(brk) SL_state[LA] = 0;
   }

   // extra adding to test
   // if(prev >= 1 && W15 && SL_state[LA] == 0) SL_state[LA] = 1;

   //--- M30 LATCH. Detection engages the state; a close outside the M30 band
   //--- releases it. Applied AFTER the M15 breakout cancel, so that cancel still
   //--- governs whether a bar is allowed to engage in the first place.
   if(SL_UseM30Latch)
   {
      double px_l  = iClose(_Symbol, PERIOD_M5, 0);
      double upp30 = BB_datas[2].BBUppLV[LA];
      double low30 = BB_datas[2].BBLowLV[LA];
      bool   out30 = (px_l > upp30 || px_l < low30);

      if(sl_latched)
      {
         if(out30) sl_latched = false;                        // released
      }
      else
      {
         if(SL_state[LA] >= 2 && !out30) sl_latched = true;   // engaged
      }
      SL_state[LA] = sl_latched ? 2 : 0;
   }

   //--- H1 block -> state 3 (needs previous bar == 2). OFF by default.
   bool A1H = false, B1H = false, C1H = false;
   if(SL_UseH1)
   {
      A1H = ( SL_StageOK((int)BB_datas[3].BBW_stage[LA])
           || (BB_datas[3].BB_diffBBW[LA] < BB_datas[3].BB_diffBBW[LA_1]
            && BB_datas[3].BB_diffBBW[LA_1] < BB_datas[3].BB_diffBBW[LA_2]) );
      B1H = (c2 < c2a && c2a < c2b) || (c3 < c3a && c3a < c3b);
      // C1H = (c1 < CL_NEAR && c1a < CL_NEAR);
      bool C1H = (c2 < CL_NEAR_H1 && c2a < CL_NEAR_H1);   // CL_NEAR_H1 ~= 30
      // if(prev == 2 && A1H && B1H && C1H) SL_state[LA] = 3;
      if(prev >= 1 && A1H && B1H && C1H) SL_state[LA] = 3;
   }

   //--- why did it fail? (for the label and log)
   //--- report the gate that blocked the level ACTUALLY reached.
   string why = "";
   if(SL_state[LA] == 0)
   {
      if(brk)       why = "brk";
      else if(!A15) why = "A15";
      else          why = "ev15";
   }
   else if(SL_state[LA] == 1)
   {
      if(prev < 1)  why = "prev";
      else if(!A30) why = "A30";
      else          why = "ev30";
   }

   //--- draw
   if(SL_Draw)
   {
      double mid = BB_datas[1].BBMidLV[LA];
      datetime t = iTime(_Symbol, PERIOD_M15, 0);
 
      // skip state-0 bars only when SL_ShowFails is off
      if(mid > 0.0 && t > 0 && (SL_state[LA] > 0 || SL_ShowFails))
      {
         string txt = "L" + IntegerToString(SL_state[LA]);
         if(why != "") txt += "-" + why;
         if(SL_DrawL1Tags && l1tags != "") txt += "[" + l1tags + "]";
 
         string name = txt + "_" + IntegerToString((int)t);   // ID only, one label per bar
         if(ObjectFind(0, name) < 0 && SL_state[LA] > 0)
         {
            color col;
            if(SL_state[LA] == 3)      col = clrAqua;
            else if(SL_state[LA] == 2) col = clrLime;
            else if(SL_state[LA] == 1) col = clrYellow;
            else                       col = clrGray;
 
            if(ObjectCreate(0, name, OBJ_TEXT, 0, t, mid + SL_TagOffsetPts * _Point))
            // if(ObjectCreate(0, name, OBJ_TEXT, 0, t, mid + SL_TagOffsetPts))
            {
               ObjectSetString (0, name, OBJPROP_TEXT,     txt);
               ObjectSetInteger(0, name, OBJPROP_COLOR,    col);
               ObjectSetInteger(0, name, OBJPROP_FONTSIZE, SL_FontSize);
               ObjectSetDouble (0, name, OBJPROP_ANGLE,    SL_Angle);
               ObjectSetInteger(0, name, OBJPROP_ANCHOR,   ANCHOR_UPPER);
               ObjectSetInteger(0, name, OBJPROP_BACK,     false);
            }
         }
      }
   }

   //--- L2 tags on their OWN label: M30 midline, at the M30 BAR TIME.
   //--- One label per M30 bar - SL_Update runs per M15 bar, so the two M15 bars
   //--- inside an M30 bar both reach here, and ObjectFind lets only the first
   //--- create it. That is harmless: l2tags is built from BB_datas[2], which only
   //--- changes when a new M30 bar forms, so both calls compute the same tags.
   //--- Independent of SL_Draw - the M30 side can be shown with the M15 side off.
   //--- One tag label per level, each on its OWN midline at its OWN bar time.
   if(SL_DrawL2Tags && l2tags != "") SL_DrawTagLabel("SLL2_", l2tags, BB_datas[2].BBMidLV[LA],
                                     PERIOD_M30, SL_L2TagColor);
   if(SL_DrawL3Tags && l3tags != "") SL_DrawTagLabel("SLL3_", l3tags, BB_datas[3].BBMidLV[LA],
                                     PERIOD_H1,  SL_L3TagColor);
   if(SL_DrawL4Tags && l4tags != "") SL_DrawTagLabel("SLL4_", l4tags, BB_datas[4].BBMidLV[LA],
                                     PERIOD_H4,  SL_L4TagColor);
   //--- SL_Draw off: still show the L1 tags on the M15 midline. L2 is NOT drawn
   //--- here - it has its own block below, on the M30 midline at the M30 bar time.
   if(SL_DrawL1Tags && l1tags != "") SL_DrawTagLabel("SLL1_", l1tags, BB_datas[1].BBMidLV[LA],
                                     PERIOD_M15,  SL_L1TagColor);
   // if(SL_DrawL1Tags && l1tags != "")
   // {
   //    double mid = BB_datas[1].BBMidLV[LA];
   //    datetime t = iTime(_Symbol, PERIOD_M15, 0);

   //    if(mid > 0.0 && t > 0)
   //    {
   //       string txt = "[L1-" + l1tags + "]";
   //       string name = txt + "_" + IntegerToString((int)t);   // ID only, one label per bar
   //       if(ObjectFind(0, name) < 0 && l1tags != "")
   //       {
   //          // if(ObjectCreate(0, name, OBJ_TEXT, 0, t, mid + SL_TagOffsetPts * _Point))
   //          if(ObjectCreate(0, name, OBJ_TEXT, 0, t, mid + SL_TagOffsetPts))
   //          {
   //             ObjectSetString (0, name, OBJPROP_TEXT,     txt);
   //             ObjectSetInteger(0, name, OBJPROP_COLOR,    SL_L1TagColor);
   //             ObjectSetInteger(0, name, OBJPROP_FONTSIZE, SL_FontSize);
   //             ObjectSetDouble (0, name, OBJPROP_ANGLE,    SL_Angle);
   //             ObjectSetInteger(0, name, OBJPROP_ANCHOR,   ANCHOR_UPPER);
   //             ObjectSetInteger(0, name, OBJPROP_BACK,     false);
   //          }
   //       }
   //    }
   // }

   //--- log, so the chart can be cross-checked against the numbers
   if(SL_WriteLog)
   {
      Print("[LADDER",  
            "] L1tags:[", (l1tags == "" ? "-" : l1tags),
            "] L2tags:[", (l2tags == "" ? "-" : l2tags),
            "] L3tags:[", (l3tags == "" ? "-" : l3tags),
            "] L4tags:[", (l4tags == "" ? "-" : l4tags), 
            "] state:[", SL_state[LA],
            "] prev:[", prev,
            "] why:[", why,
            "] L1m:[", SL_L1Mode, "] L2m:[", SL_L2Mode,
            "] A15:[", A15, "] S15:[", S15, "] C15:[", C15,
            "] A30:[", A30, "] S30:[", S30, "] C30:[", C30, "] W30:[", W30,
            "] brkmode:[", SL_BreakoutMode,
            "] brk:[", brk,
            "] c0:[", DoubleToString(c0,1),
            "] c1:[", DoubleToString(c1,1),
            "] c2:[", DoubleToString(c2,1),
            "] ws15:[", (int)BB_datas[1].BBW_stage[LA],
            "] ws30:[", (int)BB_datas[2].BBW_stage[LA], "]");
   }
   //--- Draw the label rectangles lazily. iBarShift returns -1 in OnInit during a
   //--- backtest because no history is loaded yet, so all 27 ranges were skipped.
   //--- Called here, each range appears as soon as its bars exist. The ObjectFind
   //--- guard inside makes repeat calls a no-op.
   if(SL_DrawUserLabels) SL_DrawUserLabelRanges();

   //--- DUAL VIRTUAL SIM: run USER labels and the ladder side by side.
   //--- Neither places an order; this only reports how far apart they are.
   datetime t_bar   = iTime(_Symbol, PERIOD_M15, 0);
   double   px_bar  = iClose(_Symbol, PERIOD_M5, 0);
   double   dm0_bar = BB_datas[0].BB_diffMid_Trend[LA];        // M5
   double   dm1_bar = BB_datas[1].BB_diffMid_Trend[LA];        // M15
   double   dmv_bar = (SL_TrendTF == 0) ? dm0_bar : dm1_bar;   // same choice as Trade_Strategy
   double   mid_bar = BB_datas[1].BBMidLV[LA];

   bool sw_user = SL_InUserLabel(t_bar);
   bool sw_ladd = (SL_state[LA] >= 2);
   string SWCMP_info = "";

   sv_scored++;
   if(sw_user && sw_ladd)       sv_agree++;
   else if(sw_user && !sw_ladd) sv_user_only++;
   else if(!sw_user && sw_ladd) sv_ladd_only++;

   sv_evt[0] = ""; sv_evt[1] = "";
   SL_VirtualStep(0, sw_user, dmv_bar, t_bar, px_bar);
   SL_VirtualStep(1, sw_ladd, dmv_bar, t_bar, px_bar);

   if(sw_ladd) SL_DrawLadderLabel(t_bar, mid_bar);

   //--- Track the open ladder range. A run of SL_state >= 2 bars is one range;
   //--- it is drawn when the run ENDS so the high/low span is final.
   static datetime sl_lr_last = 0;
   if(sw_ladd)
   {
      if(sl_lr_start == 0) sl_lr_start = t_bar;   // range opens
      sl_lr_last = t_bar;
   }
   else
   {
      if(sl_lr_start != 0) SL_CloseLadderRange(sl_lr_last);   // range closes
   }

   if(SL_WriteLog)
   {
      SWCMP_info = "[SWCMP] bar:[" + TimeToString(t_bar, TIME_DATE|TIME_MINUTES);
      if(sw_ladd) SWCMP_info += "] user:[" +  (sw_user ? "SW" : "--");
      if(sw_user) SWCMP_info += "] ladder:["+ (sw_ladd ? "SW" : "--");
      SWCMP_info += "] match:["+ (sw_user == sw_ladd ? "yes" : "NO");
      SWCMP_info += "] lad_state:[" + SL_state[LA] + "]";
      if(sw_user) SWCMP_info += "] U:[" + (sv_evt[0] == "" ? "-" : sv_evt[0]);
      if(sw_ladd)  SWCMP_info += "] L:["+ (sv_evt[1] == "" ? "-" : sv_evt[1]) + "]";
      Print(SWCMP_info);
      // Print("[SWCMP] bar:[", TimeToString(t_bar, TIME_DATE|TIME_MINUTES),
      //       "] user:[", (sw_user ? "SW" : "--"),
      //       "] ladder:[", (sw_ladd ? "SW" : "--"),
      //       "] match:[", (sw_user == sw_ladd ? "yes" : "NO"),
      //       "] lad_state:[", SL_state[LA], "]");
   }
}


//+------------------------------------------------------------------+
//| Trade_Strategy                                            |
//|                                                                  |
//| SAME SIGNATURE as TofyTrade6 / TofyTrade_DMonly Trade_Strategy,  |
//| but a DIFFERENT NAME so both can be included without colliding.  |
//| Dispatch from the EA:                                            |
//|                                                                  |
//|     if(SL_UseTradeStrategy)                                      |
//|        Trade_Strategy( ...same args... );                 |
//|     else                                                         |
//|        Trade_Strategy( ...same args... );                        |
//|                                                                  |
//| REQUIREMENT: SL_Update() must already have run for this bar, or  |
//| SL_state[LA] is stale. In Tofu_EA_Simple_V7 SL_Update is called  |
//| inside the M15 gate before the Trade_Strategy dispatch.          |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Trade_act codes, as consumed by Tofu_EA_Simple_V7.mq5 (line 462+) |
//|   0  no action                                                    |
//|   1  exit_sell AND entry_buy                                      |
//|   2  exit_buy  AND entry_sell                                     |
//|   3  no_exit, entry_buy      <- used here for a BUY from flat      |
//|   4  no_exit, entry_sell     <- used here for a SELL from flat     |
//|   5  exit_buy, no entry      <- used here for REVERSAL_DN          |
//|   6  exit_sell, no entry     <- used here for REVERSAL_UP          |
//|   7  exit_all                <- used here for the SIDEWAYS exit    |
//|  11  exit_sell entry_buy with ATRSL                                |
//|  12  exit_buy  entry_sell with ATRSL                               |
//|                                                                    |
//| TofyTrade_DMonly.mqh uses 1/2 for entries and 7 for every exit.     |
//| Those are EQUIVALENT here because this strategy only enters when    |
//| flat (so the exit half of 1/2 is a no-op) and only ever holds one   |
//| side (so exit_all and exit_<side> close the same thing). The codes  |
//| below are the precise ones - same behaviour, self-documenting.      |
//+------------------------------------------------------------------+
void Trade_Strategy(
   BB_MTF_Data_struct      &BB_datas[],
   ATRSLBUF_struct         &ATRSL1BUF,
   BB_MTF_Impact_struct    &BBTFImpact,
   ENUM_Trade_Act          &Trade_act,   // OUT: 0=hold 1=BUY 2=SELL 7=exit_all
   string                  &Trade_info,
   double                  &Trade_lots,
   double                  &Trade_sl,
   int                      BUYS,
   int                      SELLS,
   double                  &close_prices[],
   double                   baseLot = 0.01
)
{
   //--- Defaults: HOLD, no stop, base lot
   Trade_act = 0; Trade_info = ""; Trade_lots = baseLot; Trade_sl = 0.0;

   //--- master switch: do nothing at all unless explicitly enabled
   if(!SL_UseTradeStrategy) return;

   //--- Once-per-bar guard
   static datetime sl_lastBar = 0;
   datetime cur = iTime(_Symbol, (SL_TradeTF == 0) ? PERIOD_M5 : PERIOD_M15, 0);
   if(cur == sl_lastBar) { Trade_info = ""; return; }
   sl_lastBar = cur;

   //--- inputs
   double px_now  = iClose(_Symbol, PERIOD_M5, 0);         // same basis as the report
   double dm0     = BB_datas[0].BB_diffMid_Trend[LA];        // M5
   double dm1     = BB_datas[1].BB_diffMid_Trend[LA];        // M15
   double dm      = (SL_TrendTF == 0) ? dm0 : dm1;           // the one that decides
   int    sflag   = (int)BBTFImpact.sideway_selected[LA];  // TofySideway S_ (LA = current)
   int    ladder  = SL_state[LA];                          // ladder state for this bar

   bool sw_flag   = (sflag  > 0);
   bool sw_ladder = (ladder >= 2);

   bool sw = false;
   if(SL_ExitMode == 0)      sw = sw_ladder;
   else if(SL_ExitMode == 1) sw = sw_flag;
   else if(SL_ExitMode == 2) sw = (sw_flag && sw_ladder);
   else if(SL_ExitMode == 3) sw = (sw_flag || sw_ladder);
   else if(SL_ExitMode == 4) sw = SL_InUserLabel(cur);   // HINDSIGHT - ceiling only

   bool dm1_up   = (dm == 1.0 || dm == 5.0);
   bool dm1_down = (dm == 2.0 || dm == 4.0);

   bool inLong  = (BUYS  > 0);
   bool inShort = (SELLS > 0);
   bool flat    = (!inLong && !inShort);

   Trade_info = "[LADTRADE] dm1:" + DoubleToString(dm1,1)
              + " LAD:"   + IntegerToString(ladder)
              + " S_:"    + IntegerToString(sflag)
              + " XM:"    + IntegerToString(SL_ExitMode)
              + " BUYS:"  + IntegerToString(BUYS)
              + " SELLS:" + IntegerToString(SELLS);

   //================================================================
   // PRIORITY 1 - SIDEWAYS EXIT. Close all. Exit beats entry.
   //================================================================
   if(sw)
   {
      if(!flat)
      {
         Trade_act = 7;                       // exit_all
         Trade_info += " [LAD]SIDEWAYS_EXIT";
      }
      SL_TrackAct((int)Trade_act, cur, px_now);
      return;   // sideway bar: never enter
   }

   //================================================================
   // PRIORITY 2 - REVERSAL (opposite dm closes; NO same-bar re-entry)
   //================================================================
   if(inLong && dm1_down)
   {
      Trade_act = 5;                           // exit_buy_no_entry
      Trade_info += " [LAD]REVERSAL_DN";
      SL_TrackAct((int)Trade_act, cur, px_now);
      return;
   }
   if(inShort && dm1_up)
   {
      Trade_act = 6;                           // exit_sell_no_entry
      Trade_info += " [LAD]REVERSAL_UP";
      SL_TrackAct((int)Trade_act, cur, px_now);
      return;
   }

   //================================================================
   // PRIORITY 3 - ENTRY (only when flat)
   //================================================================
   if(flat)
   {
      if(dm1_up)
      {
         Trade_act = 3;                        // no_exit_entry_buy
         Trade_info += " [LAD]ENTRY_BUY";
      }
      else if(dm1_down)
      {
         Trade_act = 4;                        // no_exit_entry_sell
         Trade_info += " [LAD]ENTRY_SELL";
      }
      // dm == 3 (sideways family) or dm == 0 (warmup) -> stay flat
   }
   //--- ONE place the chart is updated, from whatever act was decided above
   SL_TrackAct((int)Trade_act, cur, px_now);

   // In a position, same-direction dm, no sideway -> HOLD (act stays 0),
   // so the trade rides until a reversal or a sideway exit closes it.
   // This is what let DMONLY hold winners into trends.
}

//+------------------------------------------------------------------+
//| SL_PrintSummary - call from OnDeinit.                            |
//| Reports what the run actually did, so a backtest can be checked  |
//| without counting objects on the chart.                           |
//+------------------------------------------------------------------+
void SL_PrintSummary()
{
   int trades = sl_tr_seq;
   int losses = trades - sl_win_count;
   double wr  = (trades > 0) ? 100.0 * sl_win_count / trades : 0.0;
   double pf  = (sl_loss_sum != 0.0) ? sl_win_sum / MathAbs(sl_loss_sum) : 0.0;

   Print("[LADDER_SUMMARY] ladder_ranges_drawn:[", sl_lr_seq,
         "] vs hand labels:[", SL_LABEL_COUNT, "]");
   Print("[LADDER_SUMMARY] s30waive:[", SL_S30WaivesChain,
         "] m30latch:[", SL_UseM30Latch, "]");
   Print("[LADDER_SUMMARY] mode:[", SL_ExitMode,
         "] L1m:[", SL_L1Mode, "] L2m:[", SL_L2Mode,
         "] brkmode:[", SL_BreakoutMode, "]");
   Print("[LADDER_SUMMARY] label rectangles drawn:[", sl_rect_count,
         "] of [", SL_LABEL_COUNT, "]");
   Print("[LADDER_SUMMARY] trades:[", trades,
         "] wins:[", sl_win_count,
         "] losses:[", losses,
         "] win_rate:[", DoubleToString(wr, 1), "%]");
   Print("[LADDER_SUMMARY] gross_pnl:[", DoubleToString(sl_tr_cum, 2),
         "] win_sum:[", DoubleToString(sl_win_sum, 2),
         "] loss_sum:[", DoubleToString(sl_loss_sum, 2),
         "] profit_factor:[", DoubleToString(pf, 2), "]");
   //--- side-by-side comparison of the two sideway sources
   double prec = (sv_bars[1] > 0) ? 100.0 * sv_agree / sv_bars[1] : 0.0;
   double rec  = (sv_bars[0] > 0) ? 100.0 * sv_agree / sv_bars[0] : 0.0;
   double f1   = (prec + rec > 0.0) ? 2.0 * prec * rec / (prec + rec) : 0.0;
   double wr0  = (sv_trades[0] > 0) ? 100.0 * sv_wins[0] / sv_trades[0] : 0.0;
   double wr1  = (sv_trades[1] > 0) ? 100.0 * sv_wins[1] / sv_trades[1] : 0.0;

   Print("[SWCMP_SUMMARY] scored_bars:[", sv_scored,
         "] both_sideway:[", sv_agree,
         "] user_only:[", sv_user_only,
         "] ladder_only:[", sv_ladd_only, "]");
   Print("[SWCMP_SUMMARY] USER   bars:[", sv_bars[0],
         "] ranges:[", sv_ranges[0],
         "] trades:[", sv_trades[0],
         "] win_rate:[", DoubleToString(wr0, 1),
         "%] pnl:[", DoubleToString(sv_pnl[0], 2), "]");
   Print("[SWCMP_SUMMARY] LADDER bars:[", sv_bars[1],
         "] ranges:[", sv_ranges[1],
         "] trades:[", sv_trades[1],
         "] win_rate:[", DoubleToString(wr1, 1),
         "%] pnl:[", DoubleToString(sv_pnl[1], 2), "]");
   Print("[SWCMP_SUMMARY] ladder vs user - precision:[", DoubleToString(prec, 1),
         "%] recall:[", DoubleToString(rec, 1),
         "%] f1:[", DoubleToString(f1, 1),
         "] pnl_gap:[", DoubleToString(sv_pnl[1] - sv_pnl[0], 2), "]");

   Print("[LADDER_SUMMARY] exits - sideways:[", sl_r_sideways,
         "] reversal_dn:[", sl_r_rev_dn,
         "] reversal_up:[", sl_r_rev_up, "]");
}