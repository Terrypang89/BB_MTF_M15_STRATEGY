#property copyright "Copyright 2026, terrypang."
#property link      "https://www.mql5.com/en/users/terrypang/"
#property version "36.15"
//+------------------------------------------------------------------+
//| TofyTrade_DMonly — dm-only + TofySideway + reversal (Option A)    |
//|                                                                  |
//| Live port of the Python DMONLY variant. Same call contract as    |
//| TofyTrade6.Trade_Strategy() so Tofu_EA_Simple_V7 can dispatch    |
//| to it unchanged.                                                 |
//|                                                                  |
//| RULES (exactly the Python DMONLY):                               |
//|   dm = BB_datas[1].BB_diffMid_Trend[LA]   (M15 diffMid_Trend cur)|
//|   1. SIDEWAYS exit : BBTFImpact.sideway_selected[0] > 0 -> act=7 |
//|   2. REVERSAL      : LONG & dm in {2,4} -> act=7 (close, no       |
//|                      re-entry this bar)                          |
//|                      SHORT & dm in {1,5} -> act=7                |
//|   3. ENTRY (flat)  : dm in {1,5} -> act=1 (BUY)                  |
//|                      dm in {2,4} -> act=2 (SELL)                 |
//|   NO FLY_PSHRINK / SHRINK / SQZ. W_stage NOT used for entry.     |
//|                                                                  |
//| Trade_act OUT convention (from EA):                              |
//|   0=hold  1=exit_sell+buy(BUY)  2=exit_buy+sell(SELL)  7=exit_all|
//|                                                                  |
//| REALITY WARNING: the Python DMONLY reference was 1120 trades /   |
//| +$968.93 GROSS with ZERO spread/slippage and close_M5 fills.     |
//| This live EA pays real spread (~-$390 over 1120 trades) and      |
//| fills at bid/ask, not the M5 close. Expect materially less.      |
//| Use this to VERIFY how much survives — not to tune the backtest. |
//+------------------------------------------------------------------+
#include <TofyIncludeSimple.mqh>

//--- once-per-bar SIG logging, same grammar as the other TofyTrade files
void SigEvtDM(string evt, string kvs)
{  Print("[DMONLY] SIG:DMONLY evt:", evt, kvs); }

//+------------------------------------------------------------------+
//| Trade_Strategy — SAME SIGNATURE as TofyTrade6, so the EA calls   |
//| it identically. Only the body differs.                          |
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
   //--- Defaults: HOLD, no stop, base lot (identical to TofyTrade6)
   Trade_act = 0; Trade_info = ""; Trade_lots = baseLot; Trade_sl = 0.0;

   //--- Once-per-bar guard (identical to TofyTrade6)
   static datetime s_lastBar = 0;
   datetime cur = iTime(_Symbol, PERIOD_M5, 0);
   if(cur == s_lastBar) { Trade_info = ""; return; }
   s_lastBar = cur;

   //--- The ONLY inputs DMONLY uses ---------------------------------
   double dm      = BB_datas[1].BB_diffMid_Trend[LA];      // index 1 = M15, cur
   int    sideway = (int)BBTFImpact.sideway_selected[0];   // >0 = TofySideway S_ flag

   bool dm_up   = (dm == 1.0 || dm == 5.0);   // buy / reversal-up direction
   bool dm_down = (dm == 2.0 || dm == 4.0);   // sell / reversal-dn direction

   bool inLong  = (BUYS  > 0);
   bool inShort = (SELLS > 0);
   bool flat    = (!inLong && !inShort);

   Trade_info = "[DMONLY] dm:" + DoubleToString(dm,1)
              + " S_:" + IntegerToString(sideway)
              + " BUYS:" + IntegerToString(BUYS)
              + " SELLS:" + IntegerToString(SELLS);

   //================================================================
   // PRIORITY 1 — SIDEWAYS EXIT (TofySideway S_ flag). Close all.
   //   Exit beats entry (matches Python: sideway checked first).
   //================================================================
   if(sideway > 0)
   {
      if(!flat)
      {
         Trade_act = 7;                       // exit_all
         Trade_info += " [DM]SIDEWAYS_EXIT";
         SigEvtDM("EXIT", Trade_info);
      }
      return;   // sideway bar: never enter
   }

   //================================================================
   // PRIORITY 2 — REVERSAL (opposite dm closes; NO same-bar re-entry)
   //================================================================
   if(inLong && dm_down)
   {
      Trade_act = 7;                          // close the long, wait for next bar
      Trade_info += " [DM]REVERSAL_DN";
      SigEvtDM("EXIT", Trade_info);
      return;
   }
   if(inShort && dm_up)
   {
      Trade_act = 7;                          // close the short, wait for next bar
      Trade_info += " [DM]REVERSAL_UP";
      SigEvtDM("EXIT", Trade_info);
      return;
   }

   //================================================================
   // PRIORITY 3 — ENTRY (only when flat)
   //================================================================
   if(flat)
   {
      if(dm_up)
      {
         Trade_act = 1;                        // BUY
         Trade_info += " [DM]ENTRY_BUY";
         SigEvtDM("ENTRY", Trade_info);
      }
      else if(dm_down)
      {
         Trade_act = 2;                        // SELL
         Trade_info += " [DM]ENTRY_SELL";
         SigEvtDM("ENTRY", Trade_info);
      }
      // dm == 3 (sideways family) or dm == 0 (warmup) -> stay flat (HOLD)
   }
   // If in a position with same-direction dm and no sideway: HOLD (act stays 0),
   // so the trade rides until a reversal or a TofySideway S_ flag closes it.
   // This is what let DMONLY hold winners into trends.
}
