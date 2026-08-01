//+------------------------------------------------------------------+
//| TofyVerifySideway.mqh                                            |
//|                                                                  |
//| VISUAL + LOG verification of the TofySideway S_ flag against     |
//| what price ACTUALLY did afterward.                               |
//|                                                                  |
//| Chart label (rotated 90 deg, drawn ON the M15 BB midline):       |
//|      S13-NEU = flag S_13 said sideway, price went nowhere  OK    |
//|      S13-UP  = flag said sideway, price ran up            WRONG  |
//|      S13-DN  = flag said sideway, price ran down          WRONG  |
//|      .-NEU   = no flag, but price went nowhere           MISSED  |
//|      .-UP/.-DN = no flag, price moved                        OK  |
//|                                                                  |
//| Log line (parseable, same field:[value] convention as the EA):   |
//|   [VERIFY_SIDEWAY] bar:[...] S_:[13] outcome:[NEU]               |
//|        start_px:[4345.50] mid_M15:[4348.12] barsN:[8] X:[10.0]   |
//|                                                                  |
//| Barrier (identical to label_base_rate.py, pre-registered):       |
//|   X = 10.0, N = 8 M15 bars (120 min), first touch on M5 closes.  |
//|     start+X hit first -> UP ; start-X hit first -> DN            |
//|     neither within 120 min -> NEU  (this is "sideways")          |
//|                                                                  |
//| ############# LOOKAHEAD WARNING #############                    |
//| Bar T's outcome is NOT knowable until T+120min. This file only   |
//| resolves and draws bar T-8, using price that already happened.   |
//| It is a MEASUREMENT OF THE PAST for visual checking.             |
//| NEVER read these values from trade logic — that would be         |
//| lookahead bias and would make every later backtest fake.         |
//| #############################################                    |
//+------------------------------------------------------------------+

//--- barrier parameters (keep identical to the Python test)
double VS_X          = 10.0;   // price offset that counts as "a move"
int    VS_N          = 8;      // M15 bars ahead = 120 minutes
bool   VS_DrawLabels = true;
bool   VS_WriteLog   = true;   // emit a [VERIFY_SIDEWAY] line per resolved bar
int    VS_FontSize   = 11;     // bigger than the default 8
double VS_Angle      = 90.0;   // rotate label vertical

//--- rolling history so we can resolve bar T-N
#define VS_MAX 8192
datetime vs_time[VS_MAX];
int      vs_sub [VS_MAX];      // S_ sub-type (0 = no flag)
double   vs_mid [VS_MAX];      // M15 BB midline AT that bar (label is drawn here)
int      vs_count = 0;

//--- running tally, cross-checkable against the Python report
int vs_A_up=0, vs_A_dn=0, vs_A_neu=0;   // GROUP A: S_ flag present
int vs_B_up=0, vs_B_dn=0, vs_B_neu=0;   // GROUP B: no flag

//+------------------------------------------------------------------+
//| Resolve one bar's forward outcome from ALREADY-CLOSED M5 bars.   |
//| Returns false if the 120-minute window is not fully in the past. |
//+------------------------------------------------------------------+
bool VS_Resolve(datetime t0, double &start_px, string &outcome)
{
   int s0 = iBarShift(_Symbol, PERIOD_M5, t0, false);
   if(s0 < 0) return false;

   start_px = iClose(_Symbol, PERIOD_M5, s0);
   if(start_px <= 0.0) return false;

   datetime t_end = t0 + (datetime)(VS_N * 15 * 60);   // T + 120 minutes

   // forward in time = DECREASING shift; 0 is the newest closed bar
   for(int s = s0 - 1; s >= 0; s--)
   {
      datetime ts = iTime(_Symbol, PERIOD_M5, s);
      if(ts <= 0)    break;
      if(ts > t_end) { outcome = "NEU"; return true; }   // window expired, nothing hit

      double px = iClose(_Symbol, PERIOD_M5, s);
      if(px >= start_px + VS_X) { outcome = "UP"; return true; }
      if(px <= start_px - VS_X) { outcome = "DN"; return true; }
   }
   return false;   // not enough bars yet — resolve on a later call
}

//+------------------------------------------------------------------+
//| Draw the verdict vertically, anchored on the M15 BB midline.     |
//+------------------------------------------------------------------+
void VS_DrawLabel(datetime t0, double mid_px, int sub, string outcome)
{
   if(!VS_DrawLabels) return;
   if(mid_px <= 0.0)  return;

   string name = "VS_" + IntegerToString((int)t0);
   if(ObjectFind(0, name) >= 0) return;          // already drawn

   string tag = (sub > 0) ? ("S" + IntegerToString(sub)) : ".";
   string txt = tag + "-" + outcome;

   color col;
   if(sub > 0 && outcome == "NEU")   col = clrLime;      // flag correct
   else if(sub > 0)                  col = clrRed;       // FALSE sideway
   else if(outcome == "NEU")         col = clrOrange;    // MISSED sideway
   else                              col = clrDimGray;   // correctly not sideway

   if(!ObjectCreate(0, name, OBJ_TEXT, 0, t0, mid_px)) return;
   ObjectSetString (0, name, OBJPROP_TEXT,     txt);
   ObjectSetInteger(0, name, OBJPROP_COLOR,    col);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, VS_FontSize);
   ObjectSetDouble (0, name, OBJPROP_ANGLE,    VS_Angle);      // vertical
   ObjectSetInteger(0, name, OBJPROP_ANCHOR,   ANCHOR_LOWER);  // sits on the midline
   ObjectSetInteger(0, name, OBJPROP_BACK,     false);
}

//+------------------------------------------------------------------+
//| Call ONCE per new M15 bar.                                       |
//|   t_bar        = iTime(_Symbol, PERIOD_M15, 0)                   |
//|   sideway_sub  = (int)BBTFImpact.sideway_selected[LA]  (0 = none) |
//|   mid_lv_M15   = the M15 BB midline value at this bar            |
//|                  (whatever your struct calls it, e.g.            |
//|                   BB_datas[1].BB_MidLV[LA])                      |
//+------------------------------------------------------------------+
void VS_OnNewM15Bar(datetime t_bar, int sideway_sub, double mid_lv_M15)
{
   if(vs_count < VS_MAX)
   {
      vs_time[vs_count] = t_bar;
      vs_sub [vs_count] = sideway_sub;
      vs_mid [vs_count] = mid_lv_M15;
      vs_count++;
   }

   // resolve the bar whose 120-minute window has now fully closed
   int idx = vs_count - 1 - VS_N;
   if(idx < 0) return;

   double start_px = 0.0;
   string outcome  = "";
   if(!VS_Resolve(vs_time[idx], start_px, outcome)) return;

   int sub = vs_sub[idx];
   if(sub > 0)
   {
      if(outcome == "UP")      vs_A_up++;
      else if(outcome == "DN") vs_A_dn++;
      else                     vs_A_neu++;
   }
   else
   {
      if(outcome == "UP")      vs_B_up++;
      else if(outcome == "DN") vs_B_dn++;
      else                     vs_B_neu++;
   }

   VS_DrawLabel(vs_time[idx], vs_mid[idx], sub, outcome);

   if(VS_WriteLog)
   {
      Print("[VERIFY_SIDEWAY] bar:[", TimeToString(vs_time[idx], TIME_DATE|TIME_MINUTES),
            "] S_:[", sub,
            "] outcome:[", outcome,
            "] start_px:[", DoubleToString(start_px, 2),
            "] mid_M15:[", DoubleToString(vs_mid[idx], 2),
            "] X:[", DoubleToString(VS_X, 1),
            "] N:[", VS_N, "]");
   }
}

//+------------------------------------------------------------------+
//| Call from OnDeinit for the verdict.                              |
//| THE TEST: A_NEU% must be MATERIALLY HIGHER than B_NEU%.          |
//| If they are about equal, the S_ flag carries no information      |
//| about whether price is about to go sideways.                     |
//+------------------------------------------------------------------+
void VS_PrintSummary()
{
   int nA = vs_A_up + vs_A_dn + vs_A_neu;
   int nB = vs_B_up + vs_B_dn + vs_B_neu;
   double pA = (nA > 0) ? 100.0 * vs_A_neu / nA : 0.0;
   double pB = (nB > 0) ? 100.0 * vs_B_neu / nB : 0.0;

   Print("[VERIFY_SIDEWAY_SUMMARY] X:[", DoubleToString(VS_X,1), "] N:[", VS_N, "]");
   Print("[VERIFY_SIDEWAY_SUMMARY] GROUP_A_flag n:[", nA, "] UP:[", vs_A_up,
         "] DN:[", vs_A_dn, "] NEU:[", vs_A_neu, "] NEU_pct:[", DoubleToString(pA,1), "]");
   Print("[VERIFY_SIDEWAY_SUMMARY] GROUP_B_noflag n:[", nB, "] UP:[", vs_B_up,
         "] DN:[", vs_B_dn, "] NEU:[", vs_B_neu, "] NEU_pct:[", DoubleToString(pB,1), "]");
   Print("[VERIFY_SIDEWAY_SUMMARY] VERDICT A_minus_B:[", DoubleToString(pA - pB, 1),
         "] (large positive = flag works ; near zero = flag carries no sideway info)");
}
