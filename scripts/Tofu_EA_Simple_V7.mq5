#property copyright "Copyright 2025, terrypang."
#property link      "https://www.mql5.com/en/users/terrypang/"
#property version   "37.04                         "

#ifdef __MQL4__
#else
#include <mql4compat.mqh>  // mql4compat_fix4.mqh
#include <MT4Orders.mqh>   // MT4Orders_fix.mqh
#include <TofyIncludeSimple.mqh>
#include <TofySideway.mqh>
// #include <TofyTouch.mqh>
// #include <TofyVerifySideway.mqh>
#include <TofySidewayLadder.mqh>
// #include <TofyTrade_DMonly.mqh>
#endif

input string             Basic_Settings           = "---------------------------------------------";
input string             ORDERS_COMMENT           = "V37.04";
input int                MAGIC_NUMBER             = 898989;
input enum_mode          MODE                     = 2;
input ENUM_TIMEFRAMES    Indicator_TIMEFRAME      = PERIOD_CURRENT;
//---
input string             BB_Ind_Settings          = "---------------------------------------------"; 
input ENUM_TIMEFRAMES    BB_Ind_TIMEFRAME_0       = PERIOD_M5;
input ENUM_TIMEFRAMES    BB_Ind_TIMEFRAME_1       = PERIOD_M15;
input ENUM_TIMEFRAMES    BB_Ind_TIMEFRAME_2       = PERIOD_M30;
input ENUM_TIMEFRAMES    BB_Ind_TIMEFRAME_3       = PERIOD_H1;
input ENUM_TIMEFRAMES    BB_Ind_TIMEFRAME_4       = PERIOD_H4;
input ENUM_TIMEFRAMES    BB_Ind_TIMEFRAME_5       = PERIOD_D1;
input ENUM_TIMEFRAMES    BB_Ind_TIMEFRAME_6       = PERIOD_W1;
input ENUM_TIMEFRAMES    BB_Ind_TIMEFRAME_7       = PERIOD_MN1;
input int                Bands_period             = 20;
input int                Bands_shift              = 0;
input int                BandsLV_shift            = 10;
input bool               Bands_deviation_Ena      = true;
input double             Bands_deviation          = 2.0;
input bool               Bands_deviation1_Ena     = false;
input double             Bands_deviation_1        = 1.0;
input bool               Bands_deviation3_Ena     = false;
input double             Bands_deviation_3        = 3.0;
input ENUM_APPLIED_PRICE Bands_Price              = 5;

input string             ATR1Buf_Ind_Settings     = "---------------------------------------------"; 
input uint               InpATRPeriod             = 14;
input double             InpATRCoeff              = 2.5;
input uint               InpATRPeriod_LTF         = 7;
input double             InpATRCoeff_LTF          = 0.7;
input color              Indcolor                 = clrRed;
input color              IndSidecolor             = Orange;
input bool               InpTrailEna              = true; 
input bool               InpATREna                = true;
input bool               InpTEMAEna               = true;
input bool               InpInnerATRSLEna         = true;
input int                IndTEMAPeriod            = 3;
input uint               IndTEMAShift             = 0;
input ENUM_APPLIED_PRICE IndTEMAPrice             = 6;
input ENUM_APPLIED_PRICE IndTEMAHighPrice         = 3;
input ENUM_APPLIED_PRICE IndTEMALowPrice          = 4;

input string            Line1_Ind_Settings         = "---------------------------------------------"; 
input bool              InpLine1Ena                = true;
input ENUM_Line_Type    IndLine1Type               = 0;
input int               IndLine1Period             = 3;
input int               IndLine1Shift              = 0;
input ENUM_MA_METHOD    IndLine1Method             = 0; // MA Methid
input ENUM_APPLIED_PRICE IndLine1Price             = 3;
input color             IndLine1color              = White;

input string            Line2_Ind_Settings         = "---------------------------------------------"; 
input bool              InpLine2Ena                = true;
input ENUM_Line_Type    IndLine2Type               = 0;
input int               IndLine2Period             = 3;
input int               IndLine2Shift              = 0;
input ENUM_MA_METHOD    IndLine2Method             = 0; // MA Methid
input ENUM_APPLIED_PRICE IndLine2Price             = 4;
input color             IndLine2color              = White;

input string            ATROffset_Ind_Settings     = "---------------------------------------------"; 
input bool              InpATROffsetEna            = true;
input int               IndATRPeriod               = 14;
input double            IndATROffsetValue          = 0.7;

input string             Fixed_Points_Ind_Settings= "---------------------------------------------"; 
input int                DISTANCE                 = 50;
//---
input string             Bars_Settings            = "---------------------------------------------"; 
input bool               Enable_SpecbarOpenTime   = true;
input ENUM_TIMEFRAMES    barOpenTime              = PERIOD_CURRENT;
//---
input string             Lot_Settings             = "---------------------------------------------"; 
input ENUM_LOT           Lot_Management           = 1;
input double             VOLUME                   = 0.01;
input int                FROM_BALANCE             = 1000;
input double             RISK_PER_TRADE           = 0.0;
// set target by indicator
input string             Stoploss_Takeprofit_Settings = "---------------------------------------------"; 
input bool               Enable_SL_TAKEPROFIT     = false;
input int                TAKEPROFIT               = 500;
input int                STOPLOSS                 = -1;
input bool               Enable_CloseTradeByInd   = true;
//---
input string             Trading_Hours_Settings   = "---------------------------------------------"; 
input string             START_TIME               = "00:00";
input string             END_TIME                 = "00:00";
//---
input string             Graphic_Settings         = "---------------------------------------------";
input bool               Show_plot                = true;
input int                TIMER_SEC                = 10;
input bool               Debug_mode               = true;
input string             Font                     = "Verdana";
input int                FontSize                 = 10;
input color              BBColor_0                = Aqua;
input color              BBColor_1                = Goldenrod;
input color              BBColor_2                = GreenYellow;
input color              BBColor_3                = Red;
input color              BBColor_4                = Yellow;
input color              BBColor_5                = Magenta;
input color              BBColor_6                = LightCyan;
input color              BBColor_7                = MistyRose;
input string             Display_Settings         = "---------------------------------------------";
input bool               Cluster_Label_Ena        = false;
input bool               Verify_Label_Ena         = false;
input bool               Verify_Log_Ena           = true;
input group "=== Ladder: core trade settings ==="
input bool               Ladder_UseTrade_Ena      = true;   // master switch for Trade_Strategy
input int                Ladder_Exit_Mode         = 5;   // 0=ladder 1=S_flag 2=both 3=either 4=hand-labels(hindsight) 5=SwState(hindsight)
input int                Ladder_TrendTF           = 0;   // 0 = M5, 1 = M15
input int                Ladder_TradeTF           = 1;   // 0 = M5, 1 = M15

input group "=== Ladder: state-machine tuning ==="
input int                Ladder_L1_Mode           = 5;
input int                Ladder_L2_Mode           = 0;
input int                Ladder_Breakout_Mode     = 2;
input bool               Ladder_UseM30Latch       = true;
input bool               Ladder_S30WaivesChain    = true;

input group "=== Ladder: diagnostics / display (no effect on trades) ==="
input bool               Ladder_Label_Ena         = false;
input bool               Ladder_Log_Ena           = true;
input bool               Ladder_UserLabel_Ena     = true;
input bool               Ladder_Trade_Draw_Ena    = true;
input bool               Ladder_Virtual_User_Ena  = true;   // Magenta - user labels
input bool               Ladder_Virtual_Ladd_Ena  = false;   // blue   - ladder
input int                Ladder_LabelSource       = 1;   // 0 = HAND LABELS (ground truth), 1 = FITTED boundaries (hindsight - measurement only)

// #define TF_ANUM 7 // timeframe array number, 0,1,2,3,4,5,6,7
// #define LA 4 // latest array number
// #define LA_1 3 // previous array number
// #define LA_2 2 // previous 2nd array number
// #define LA_3 1 // previous 3rd array number
// #define LA_4 0 // previous 4th array number

string IndicatorName = "TOFY"; 

bool CLOSE_BUY=false,CLOSE_SELL=false,CLOSE_ALL=false;
double BUY_PROFIT=0,SELL_PROFIT=0,BUY_LOTS=0,SELL_LOTS=0;
int OPEN_BUY_TICKET_NUM= 0, OPEN_SELL_TICKET_NUM=0;
double TICKVALUE=0;
bool DEINIT = false;

int BUYS=0, SELLS=0, BUYLIMITS=0, SELLLIMITS=0, BUYSTOPS=0, SELLSTOPS=0, PREV_BUYS=0,PREV_SELLS=0;

double LAST_BID=0, LAST_LOT=0;
int WIN_TYPE=0,WIN_TICKET=0, LOSS_TYPE=0,LOSS_TICKET=0;
double WIN_PROFIT=0,WIN_LOT=0, LOSS_PROFIT=0,LOSS_LOT=0;
double LAST_BUY_PRICE=0,LAST_BUY_LOT=0,LAST_SELL_PRICE=0,LAST_SELL_LOT=0;

double handle_iTEMA_High, handle_iTEMA_Low, handle_iTEMA, handle_iATR;
double TOTAL_PROFIT=0.0, TOTAL_SWAP = 0.0;
double BUY_PRICE=0.0,SELL_PRICE=0.0;
int INP_TIME=TIMER_SEC;

ENUM_Trade_Act Trade_act;

datetime lastTFBarTime[TF_ANUM+1], lastplotTFBarTime[TF_ANUM+1], currentTFBarTime[TF_ANUM+1], M15BarTime, TIME_CURRENT=TimeCurrent();
MqlDateTime timeStruct;

double close_prices[], high_prices[], low_prices[];

// static datetime TIMER;
bool IsNewBar = false;
bool debug_info = Debug_mode;
int ATRSLBUF_count;
int print_init = 1;
string midline_Cluster_log = "";

string tradeInfo;
double tradeLots, tradeSL;
double LOT;   // declare variable

ENUM_TIMEFRAMES timeframe_list[TF_ANUM+1] = {BB_Ind_TIMEFRAME_0, BB_Ind_TIMEFRAME_1, BB_Ind_TIMEFRAME_2, BB_Ind_TIMEFRAME_3, BB_Ind_TIMEFRAME_4, BB_Ind_TIMEFRAME_5, BB_Ind_TIMEFRAME_6, BB_Ind_TIMEFRAME_7};
color color_list[TF_ANUM+1] = {BBColor_0, BBColor_1, BBColor_2, BBColor_3, BBColor_4, BBColor_5, BBColor_6, BBColor_7};
//| Expert initialization function
int OnInit()
{
  // OnInit:
#ifdef HAS_TOFYSIDEWAY
   DC_Draw = Cluster_Label_Ena;      // TofySideway.mqh cluster-label display toggle
#endif
#ifdef HAS_TofyVerifySideway
   VS_DrawLabels = Verify_Label_Ena;  // TofyVerifySideway.mqh chart labels
   VS_WriteLog   = Verify_Log_Ena;    // TofyVerifySideway.mqh [VERIFY_SIDEWAY] log lines
#endif
#ifdef HAS_TOFYSIDEWAY_LADDER
   SL_Draw       = Ladder_Label_Ena;  // TofySidewayLadder.mqh chart labels
   SL_WriteLog   = Ladder_Log_Ena;    // TofySidewayLadder.mqh [LADDER] log lines
   SL_DrawUserLabels = Ladder_UserLabel_Ena;  // draw the SIDEWAY_LABELS_FEB ranges
   SL_DrawTrades     = Ladder_Trade_Draw_Ena; // draw each trade as a segment + P&L
   SL_ExitMode       = Ladder_Exit_Mode;      // 0 ladder 1 S_flag 2 both 3 either 4 labels
   SL_UseTradeStrategy = Ladder_UseTrade_Ena;  // master switch for Trade_Strategy
   SL_DrawVirtual[0] = Ladder_Virtual_User_Ena;   // USER-label virtual run
   SL_DrawVirtual[1] = Ladder_Virtual_Ladd_Ena;   // ladder virtual run
   SL_L1Mode = Ladder_L1_Mode;
   SL_L2Mode = Ladder_L2_Mode;
   SL_BreakoutMode = Ladder_Breakout_Mode;
   SL_TradeTF = Ladder_TradeTF;
   SL_TrendTF = Ladder_TrendTF;
   SL_S30WaivesChain = Ladder_S30WaivesChain;
   SL_UseM30Latch = Ladder_UseM30Latch;
   SL_LabelSource = Ladder_LabelSource;  // pass the input to the ladder
   SL_DrawUserLabelRanges();              // draws 27 rectangles; no-op when toggle is false
#endif
   //Stats_Init();
   TIME_CURRENT=TimeCurrent();
   if(print_init){
      Print("Symbol name of the current chart=",_Symbol);
      Print("PERIOD_CURRENT of the current chart=",PERIOD_CURRENT);
      Print("Timeframe of the current chart=",_Period);
   }
   ATRSLBUF_count = 0;
   
   if(INP_TIME>60)
      INP_TIME=60;
   
   M15BarTime = 0;
   ArrayFill(currentTFBarTime,0,TF_ANUM,0);
   ArrayFill(lastTFBarTime,0,TF_ANUM,0);
   ArrayFill(lastplotTFBarTime,0,TF_ANUM,0);
   BBTFImpact_init(BBTFImpact);
   ATRSLBUF_init(ATRSL1BUF);
   TOTAL_PROFIT=0.0;

   EventSetTimer(1);
   LAST_BID    = Bid;
   TesterHideIndicators(true);
   handle_iTEMA = iTEMA(_Symbol,Indicator_TIMEFRAME,IndTEMAPeriod,IndTEMAShift,IndTEMAPrice);
   if(handle_iTEMA==INVALID_HANDLE){
      Print("iTEMA handler issue at function ", __FUNCTION__, " ", __LINE__, " ERROR: ", GetLastError());
      return -1;
   }
   handle_iATR = iATR(_Symbol, Indicator_TIMEFRAME, InpATRPeriod);
   if (handle_iATR==INVALID_HANDLE){
      Print("iATR copybuffer issuet at function:", __FUNCTION__, " ", __LINE__, " ERROR: ", GetLastError());
      return -1;
   }

   if(InpTEMAEna){
      handle_iTEMA_High=iTEMA(_Symbol, Indicator_TIMEFRAME, IndTEMAPeriod, IndTEMAShift, IndTEMAHighPrice);
      if (handle_iTEMA_High==INVALID_HANDLE){
         Print("handle_iTEMA_High issuet at function:", __FUNCTION__, " ", __LINE__, " ERROR: ", GetLastError());
         return(INIT_FAILED);
      }
      handle_iTEMA_Low=iTEMA(_Symbol, Indicator_TIMEFRAME, IndTEMAPeriod, IndTEMAShift, IndTEMALowPrice);
      if (handle_iTEMA_Low==INVALID_HANDLE){
         Print("handle_iTEMA_Low issuet at function:", __FUNCTION__, " ", __LINE__, " ERROR: ", GetLastError());
         return(INIT_FAILED);
      }
   }
   
   TesterHideIndicators(false);

   for(int i=0; i<(TF_ANUM+1); i++)
   {
      BBTFData_init(BB_datas[i], timeframe_list[i], color_list[i]);
      BBThres_assign(timeframe_list[i], BBThres[i]);
      
      if(_Period <= arraynum_2_TF(i))
      {
         if(i==7) Print("running_7!!");
         BB_datas[i].handle_BB_TEMA_MTF = iCustom(_Symbol, Indicator_TIMEFRAME, "BB_squeeze_TEMA_expert_MTF_V3", BB_datas[i].BB_Ind_TIMEFRAME, \
            Bands_deviation_Ena, Bands_period, Bands_shift, Bands_deviation, Bands_Price, BandsLV_shift, BB_datas[i].BBcolor, BB_datas[i].BBcolor, \
            Bands_deviation1_Ena, Bands_period, Bands_shift, Bands_deviation_1, Bands_Price, BB_datas[i].BBcolor, \
            Bands_deviation3_Ena, Bands_period, Bands_shift, Bands_deviation_3, Bands_Price, BB_datas[i].BBcolor, \
            false, IndTEMAPeriod, IndTEMAShift, IndTEMAHighPrice, IndTEMALowPrice, BB_datas[i].BBcolor, BB_datas[i].BBcolor);
         if (BB_datas[i].handle_BB_TEMA_MTF==INVALID_HANDLE){
            Print("handle_BB_TEMA_MTF at ",i," with tf of ",arraynum_2_string(i)," iCustom issue at function:", __FUNCTION__, " ", __LINE__, " ERROR: ", GetLastError());
            return -1;
         }
      }
   }

   TICKVALUE=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   return(INIT_SUCCEEDED);
}
//| Expert deinitialization function
void OnDeinit(const int reason)
  {
   //Stats_Print();
   EventKillTimer();
   DEINIT=true;
   DEINIT_ATRSLBUFLINE();
   ObjectsDeleteAll(0, IndicatorName + "-STAGE-");
#ifdef HAS_TofyVerifySideway
   VS_PrintSummary();
#endif
#ifdef HAS_TOFYSIDEWAY_LADDER
   SL_PrintSummary();
#endif
   Print("Deinit from reason:", reason);
  }

void OnTimer()
{
   OnTick();
}

void OnTick()
{
   TIME_CURRENT = TimeCurrent();
   BUY_PROFIT=BUY_LOTS=SELL_PROFIT=SELL_LOTS=OPEN_BUY_TICKET_NUM=OPEN_SELL_TICKET_NUM=0;
   TOTAL_VALUE(BUY_PROFIT,BUY_LOTS,SELL_PROFIT,SELL_LOTS,OPEN_BUY_TICKET_NUM, OPEN_SELL_TICKET_NUM, MAGIC_NUMBER);

   BUYS=SELLS=BUYLIMITS=SELLLIMITS=BUYSTOPS=SELLSTOPS=0;
   COUNT_ORDERS(BUYS,SELLS,BUYLIMITS,SELLLIMITS,BUYSTOPS,SELLSTOPS,MAGIC_NUMBER);

   // perform trailing stoploss, TRAILING_STOP = 50, BREAKEVEN_STOP = -1, STOPLOSS = -1, TAKEPROFIT = 500
   if(MODE < 3)
   {
      LAST_BUY_PRICE=LAST_BUY_LOT=LAST_SELL_PRICE=LAST_SELL_LOT=0;
      OPENED_VALUES(LAST_BUY_PRICE,LAST_BUY_LOT,LAST_SELL_PRICE,LAST_SELL_LOT);

      // perform close from trailing stop
      string CLOSE_info = "";
      if(CLOSE_BUY==true)
      {
         if(BUYS>0){
            CLOSE_info += "CLOSE_info ORDERS_CLOSE(OP_BUY)";
            ORDERS_CLOSE(OP_BUY);
         }
         if(BUYS==0)
            CLOSE_BUY=false;
      }
      if(CLOSE_SELL==true)
      {
         if(SELLS>0){
            CLOSE_info += "CLOSE_info ORDERS_CLOSE(OP_SELL)";
            ORDERS_CLOSE(OP_SELL);
         }
         if(SELLS==0) CLOSE_SELL=false;
      }
      if(CLOSE_ALL==true)
      {
         if(BUYS+SELLS>0){
            CLOSE_info += "CLOSE_info ORDERS_CLOSE(-1)";
            ORDERS_CLOSE(-1);
         }
         if(BUYS+SELLS==0) CLOSE_ALL=false;
      }
      if(CLOSE_info!="" && debug_info ) Print(TIME_CURRENT + " CLOSE_info " + CLOSE_info);
   }

   // set new bar entry detection 
   if(Enable_SpecbarOpenTime)
   {
      if(barOpenTime != 0 && barOpenTime > _Period){
         Print("barOpenTime must be lower than current period:" + _Period);
         Print(__FUNCTION__, " ", __LINE__, " ERROR: ", GetLastError());
         Sleep(1000);
         return;
      }
      DetectNewBar(barOpenTime);
   }
   else IsNewBar=true;

    // get prevtime 
    datetime TIME_PREV1 = iTime(_Symbol,_Period,1);
    datetime TIME_PREV2 = iTime(_Symbol,_Period,2);

   // set new bar detection 
   if(WORKING_HOURS(START_TIME,END_TIME)==true && IsNewBar)
   {
      CopyClose(_Symbol, Indicator_TIMEFRAME, 0, 5, close_prices);
      CopyHigh(_Symbol, Indicator_TIMEFRAME, 0, 5 , high_prices);
      CopyLow(_Symbol, Indicator_TIMEFRAME, 0, 5, low_prices);
      print_orderinfo(debug_info, MODE, BUY_PROFIT, BUY_LOTS, OPEN_BUY_TICKET_NUM, BUYS, SELL_PROFIT, SELL_LOTS, OPEN_SELL_TICKET_NUM, SELLS);
      // get the lot from LOT_CALCULATE(0.0, -1, 1000, 0.01)
      LOT = LOT_CALCULATE(RISK_PER_TRADE, STOPLOSS, FROM_BALANCE, VOLUME);

      if(LOT == -1)
      {
         Print(__FUNCTION__, " ", __LINE__, " ERROR: ", GetLastError());
         Sleep(1000);
         return;
      }

      string STRATEGY_6_info = "";
      string TRADE_comment = "";
      string Trade_info = "";
   
      TimeToStruct(TIME_CURRENT, timeStruct);
      string comb_stage_log = "";
      string stage_debug_log = "";
      string midtrend_debug_log = "";

      int Text_angle = 90;
      double Text_loc = 0;
      string M15_MidTrend_log = "";

      // M5 to W1
      for (int r = 0; r < TF_ANUM; r++)
      {
         comb_stage_log = "";
         if(BB_datas[r].handle_BB_TEMA_MTF >= 0)
         {
            // update the TFBartime
            if(r == 0) currentTFBarTime[r] = iTime(_Symbol, PERIOD_M5, 0);
            else if(r == 1) currentTFBarTime[r] = iTime(_Symbol, PERIOD_M15, 0);
            else if(r == 2) currentTFBarTime[r] = iTime(_Symbol, PERIOD_M30, 0);
            else if(r == 3) currentTFBarTime[r] = iTime(_Symbol, PERIOD_H1, 0);
            else if(r == 4) currentTFBarTime[r] = iTime(_Symbol, PERIOD_H4, 0);
            else if(r == 5) currentTFBarTime[r] = iTime(_Symbol, PERIOD_D1, 0);
            else if(r == 6) currentTFBarTime[r] = iTime(_Symbol, PERIOD_W1, 0);
            else if(r == 7) currentTFBarTime[r] = iTime(_Symbol, PERIOD_MN1, 0);

            if(currentTFBarTime[r] != lastTFBarTime[r])
            {
               lastTFBarTime[r] = currentTFBarTime[r];
               if(BB_strategy(BB_datas[r], BBThres[r], BBTFImpact, close_prices, high_prices, low_prices, stage_debug_log, midtrend_debug_log, BB_datas) < 0)
               {
                  Print(__FUNCTION__, " ", __LINE__, " ERROR with BB_strategy when arraynum is " + r + ": ", GetLastError());
                  Sleep(1000);
                  return;
               }
            }
         }
      }

#ifdef HAS_TOFYTOUCH
      BBDatas_Cross_BBLines(BBTFImpact, BB_datas, close_prices, high_prices, low_prices);
      // verify termination of fly by checking distance of fly_BBTarget BBUp/ BBDn 
      // check if close price has crossedup BBUp or crosseddn BBDn 
      BBTFImpact_Price_Dist_2_BBLines(BBTFImpact, BB_datas, close_prices, high_prices, low_prices);

      BBDatas_Sequence_Cross_BBLines(BBTFImpact, BB_datas, close_prices, high_prices, low_prices);

      BBDatas_Sequence_Touch_BBLines(BBTFImpact, BB_datas, TIME_CURRENT);
#endif
#ifdef HAS_TOFYSIDEWAY
      BBDatas_Midline_Cluster(BBTFImpact, BB_datas);
#endif
      if(InpInnerATRSLEna)
      {
         if(get_inner_1bufATRSL(InpATRCoeff, InpTrailEna, InpATREna, InpTEMAEna, ATRSL1BUF, handle_iTEMA, handle_iATR) < 0){
            Print(__FUNCTION__, " ", __LINE__, " ERROR with get_inner_1bufATRSL: ", GetLastError());
            Sleep(1000);
            return;
         }
      }

      // trade in M15
      if(M15BarTime != currentTFBarTime[1])
      {
         int r = 1;
         M15BarTime = currentTFBarTime[r];
#ifdef HAS_TOFYSIDEWAY
         BBDatas_Midline_Sideway(BBTFImpact, BB_datas);
#endif
#ifdef HAS_TofyVerifySideway
         VS_OnNewM15Bar(iTime(_Symbol, PERIOD_M15, 0),
               (int)BBTFImpact.sideway_selected[LA],
               BB_datas[1].BBMidLV[LA]);     // <-- your actual midline field name
#endif
      }
#ifdef HAS_TOFYSIDEWAY_LADDER
      SL_Update(BBTFImpact, BB_datas);
#endif

      if(ATRSL1BUF.ATRLV[LA] != 0.0 && ATRSL1BUF.ATRLV[LA_1] != 0.0)
      {
         Trade_act = 0;
         if(Enable_CloseTradeByInd && MODE < 3)
         {
#ifdef HAS_TOFYSIDEWAY_LADDER
            Trade_Strategy(
               BB_datas,       // your multi-TF BB array
               ATRSL1BUF,     // ATRSL struct populated each tick
               BBTFImpact,     // AllTF struct from your log parser
               Trade_act,
               tradeInfo,
               tradeLots,
               tradeSL,
               BUYS,
               SELLS,
               close_prices,
               0.01            // your base lot size
            );
#endif
            // perform real trade
            if(Trade_act != 0)
            {
               if(Trade_act == 1) // exit_sell_entry_buy
               {
                  if(SELLS>0)
                  {
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "CloseS";
                     ORDERS_CLOSE(OP_SELL, OPEN_SELL_TICKET_NUM, LOT, Trade_info);
                  }
                  if(BUYS==0 && (MODE==2||MODE==0))
                  {
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "OpenB";
                     ORDER_SEND(OP_BUY,LOT,TRADE_comment,MAGIC_NUMBER, Trade_info);
                  }
               }
               else if(Trade_act == 2) // exit_buy_entry_sell
               {
                  if(BUYS>0)
                  {
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "CloseB";
                     ORDERS_CLOSE(OP_BUY, OPEN_BUY_TICKET_NUM, LOT, Trade_info);
                  }
                  if(SELLS==0 && (MODE==1||MODE==2))
                  {
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "OpenS";
                     ORDER_SEND(OP_SELL,LOT,TRADE_comment,MAGIC_NUMBER, Trade_info);
                  }
               }
               else if(Trade_act == 3) // no_exit_entry_buy
               {
                  if(BUYS==0 && (MODE==2||MODE==0))
                  {
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "OpenB";
                     ORDER_SEND(OP_BUY,LOT,TRADE_comment,MAGIC_NUMBER, Trade_info);
                  }
               }
               else if(Trade_act == 4) // no_exit_entry_sell
               {
                  if((MODE==1||MODE==2))
                  {
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "OpenS";
                     ORDER_SEND(OP_SELL,LOT,TRADE_comment,MAGIC_NUMBER, Trade_info);
                  }
               }
               else if(Trade_act == 5) // exit_buy_no_entry
               {
                  if(BUYS>0)
                  {
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "CloseB";
                     ORDERS_CLOSE(OP_BUY, OPEN_BUY_TICKET_NUM, LOT, Trade_info);
                  }
               }
               else if(Trade_act == 6) // exit_sell_no_entry
               {
                  if(SELLS>0)
                  {
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "CloseS";
                     ORDERS_CLOSE(OP_SELL, OPEN_SELL_TICKET_NUM, LOT, Trade_info);
                  }
               }
               else if(Trade_act == 7) // exit_all
               {
                  if(SELLS>0)
                  {
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "CloseS";
                     ORDERS_CLOSE(OP_SELL, OPEN_SELL_TICKET_NUM, LOT, Trade_info);
                  }
                  if(BUYS>0)
                  {
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "CloseB";
                     ORDERS_CLOSE(OP_BUY, OPEN_BUY_TICKET_NUM, LOT, Trade_info);
                  }
               }
               else if(Trade_act == 11) // exit_sell_entry_buy_ATRSL
               {
                  if(BUYS==0 && (MODE==2||MODE==0) && BBTFImpact.TradeAct_ATRSL_Tracker == 0)
                  {
                     BBTFImpact.TradeAct_ATRSL_Tracker = 1;
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "OpenB";
                     ORDER_SEND(OP_BUY,LOT,TRADE_comment,MAGIC_NUMBER, Trade_info);
                  }
               }
               else if(Trade_act == 12) // exit_buy_entry_sell_ATRSL
               {
                  if(SELLS==0 && (MODE==2||MODE==1) && BBTFImpact.TradeAct_ATRSL_Tracker == 0)
                  {
                     BBTFImpact.TradeAct_ATRSL_Tracker = 1;
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "OpenB";
                     ORDER_SEND(OP_SELL,LOT,TRADE_comment,MAGIC_NUMBER, Trade_info);
                  }
               }
            }

            // track by atrsl
            if(BBTFImpact.TradeAct_ATRSL_Tracker == 1)
            {
               // hold buy until atrsl lower drop
               if(ATRSL1BUF.ATRTrend[LA] == 1 && ATRSL1BUF.ATRTrend[LA_1] == 1)
               {
                  if(BUYS>0) // check if purchased
                  {
                     BBTFImpact.TradeAct_ATRSL_Tracker = 0;
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "CloseB";
                     ORDERS_CLOSE(OP_BUY, OPEN_BUY_TICKET_NUM, LOT, Trade_info);
                  }
               }
               else if(ATRSL1BUF.ATRTrend[LA] == 2 && ATRSL1BUF.ATRTrend[LA_1] == 2)
               {
                  if(SELLS>0) // check if sold
                  {
                     BBTFImpact.TradeAct_ATRSL_Tracker = 0;
                     if(TRADE_comment != "") TRADE_comment += "-";
                     TRADE_comment += "CloseS";
                     ORDERS_CLOSE(OP_SELL, OPEN_SELL_TICKET_NUM, LOT, Trade_info);
                  }
               }
            }
         }
      }

      // perform draw label and print
      for (int r = 0; r < TF_ANUM; r++)
      {
         if(currentTFBarTime[r] != lastplotTFBarTime[r])
         {
            lastplotTFBarTime[r] = currentTFBarTime[r];
            print_BBdata(BB_datas[r], BBTFImpact, stage_debug_log, midtrend_debug_log, debug_info, r);
            if(Show_plot && r >= 0)
            {
               if(BB_datas[r].BBW_stage[LA] >= 400 && BB_datas[r].BBW_stage[LA] < 500)
               {
                  comb_stage_log = arraynum_2_string(r) + "-" + stage_debug_log + "-" + "SQZ";
                  if(BB_datas[r].BBW_updated_stage[LA] >= 1000)
                     comb_stage_log += "-@@@";
               }
               else if(BB_datas[r].BBW_stage[LA] >= 500)
               {
                  comb_stage_log = arraynum_2_string(r) + "-fly++";
                  if(BB_datas[r].BBW_stage[LA] == 512 || BB_datas[r].BBW_stage[LA] == 522)
                  {
                     if(BB_datas[r].BB_diffBBW[LA] > 0)
                     {
                        comb_stage_log = arraynum_2_string(r) +  "-fly+-";
                     }
                     else if(BB_datas[r].BB_diffBBW[LA] < 0)
                     {
                        comb_stage_log = arraynum_2_string(r) + "-fly-+";
                     }
                  }
                  else if(BB_datas[r].BBW_stage[LA] == 513 || BB_datas[r].BBW_stage[LA] == 523)
                  {
                     comb_stage_log = arraynum_2_string(r) + "-fly--";
                  }
               }
               else if(BB_datas[r].BBW_stage[LA] >= 300 && BB_datas[r].BBW_stage[LA] < 400)
               {
                  comb_stage_log = arraynum_2_string(r) + "-SW";
               }
               else if(BB_datas[r].BBW_stage[LA] >= 200 && BB_datas[r].BBW_stage[LA] < 300)
               {
                  comb_stage_log = arraynum_2_string(r) + "-STR";
               }

               if(comb_stage_log != "")
               {
                  Text_angle = 90;
                  DRAW_LABEL(comb_stage_log, TIME_CURRENT, BB_datas[r].BB0Up[LA_1], BB_datas[r].BBcolor, BB_datas[r].BBFontSize, BB_datas[r].BBArrowWidth, Text_angle, ANCHOR_LEFT, BB_datas[r]);
               }
               comb_stage_log = "";
               if(BB_datas[r].BB_diffMid_Trend[LA] >= 3 )
               {
                  comb_stage_log = BB_datas[r].BB_diffMid_Trend[LA];
                  // if(r == 1) M15_MidTrend_log = BB_datas[r].BB_diffMid_Trend[LA];
                  if(r == 1)
                  {
                     if(BBTFImpact.sideway_selected[LA] > 0)
                     {
                        comb_stage_log += "-";
                        comb_stage_log += IntegerToString(BBTFImpact.sideway_val[4]) + IntegerToString(BBTFImpact.sideway_val[3]) + IntegerToString(BBTFImpact.sideway_val[2]) + IntegerToString(BBTFImpact.sideway_val[1]) + IntegerToString(BBTFImpact.sideway_val[0]);
                        comb_stage_log += "-S_" + BBTFImpact.sideway_selected[LA];
                     }
                  }
                  // Text_angle = 0;
               }
               if(BB_datas[r].BB_trend[LA] == 7)
               {
                  comb_stage_log += "-REVUP";
                  if(r == 1) M15_MidTrend_log += "-REVUP";
                  // Text_angle = 90;
               }
               else if(BB_datas[r].BB_trend[LA] == 8)
               {
                  comb_stage_log += "-REVDN";
                  if(r == 1) M15_MidTrend_log += "-REVDN";
                  // Text_angle = 90;
               }
               if(comb_stage_log != "")
               {
                  Text_angle = 270;
                  Text_loc = BB_datas[r].BBMidLV[LA_1] - 2 ;
                  DRAW_LABEL(comb_stage_log, TIME_CURRENT, Text_loc, BB_datas[r].BBcolor, BB_datas[r].BBFontSize, BB_datas[r].BBArrowWidth, Text_angle, ANCHOR_UPPER, BB_datas[r]);
                  // DRAW_LABEL("-" + midline_Cluster_log + "--" + BBTFImpact.sideway_selected[0], TIME_CURRENT, Text_loc, BB_datas[1].BBcolor, 9, 2, Text_angle, ANCHOR_UPPER, BB_datas[1]);
               }

               // draw BBline_seq_touch
               comb_stage_log = "";
               if( BB_datas[r].BBline_seq_touch[LA] == 9 || BB_datas[r].BBline_seq_touch[LA] == 19)
               {
                  comb_stage_log += BB_datas[r].BBline_seq_touch[LA];
                  if(BB_datas[r].BBline_seq_touch[LA] > 10) Text_angle = 0;
                  else Text_angle = 180;
                  Text_loc = high_prices[LA];
               }
               else if(BB_datas[r].BBline_seq_touch[LA] == 8 || BB_datas[r].BBline_seq_touch[LA] == 18)
               {
                  comb_stage_log += CircledNum((int)BB_datas[r].BBline_seq_touch[LA]);   // NEW: circled
                  if(BB_datas[r].BBline_seq_touch[LA] > 10) Text_angle = 0;
                  else Text_angle = 180;
                  Text_loc = low_prices[LA];
               }
               else if(BB_datas[r].BBline_seq_touch[LA] == 7 || BB_datas[r].BBline_seq_touch[LA] == 17)
               {
                  comb_stage_log += CircledNum((int)BB_datas[r].BBline_seq_touch[LA]);   // NEW: circled
                  if(BB_datas[r].BBline_seq_touch[LA] > 10)
                  {
                     Text_angle = 180;
                  }
                  else 
                  {
                     Text_angle = 0;
                  }
                  Text_loc = high_prices[LA];
               }
               else if(BB_datas[r].BBline_seq_touch[LA] == 6 || BB_datas[r].BBline_seq_touch[LA] == 16)
               {
                  comb_stage_log += CircledNum((int)BB_datas[r].BBline_seq_touch[LA]);   // NEW: circled
                  if(BB_datas[r].BBline_seq_touch[LA] > 10)
                  {
                     Text_angle = 180;
                  }
                  else 
                  {
                     Text_angle = 0;
                  }
                  Text_loc = low_prices[LA];
               }
               if(comb_stage_log != "" && r >= 1)
               {
                  DRAW_LABEL(comb_stage_log, TIME_CURRENT, Text_loc, BB_datas[r].BBcolor, BB_datas[r].BBFontSize, BB_datas[r].BBArrowWidth, 0, ANCHOR_LEFT, BB_datas[r]);
               }
            }
         
            if(Show_plot && r == 0)
            {
               // OBJECT_ATRSLBUFLINE("ATRSLBUF" + " " + "atrsl_slmid" + "_" + (string)ATRSLBUF_count,atrsl_slmid[3],"atrsl_slmid",Yellow,3, TIME_PREV1, TIME_PREV2, atrsl_slmid[2], atrsl_slmid[3]);
               if(ATRSL1BUF.ATRLV[LA_1]!= 0 && ATRSL1BUF.ATRLV[LA_2]!= 0)
                  OBJECT_ATRSLBUFLINE("ATRSLBUF" + " " + "atrsl_lv" + "_" + (string)ATRSLBUF_count,ATRSL1BUF.ATRLV[LA_1],"atrsl_lv",Yellow,5, TIME_PREV1, TIME_PREV2, ATRSL1BUF.ATRLV[LA_2], ATRSL1BUF.ATRLV[LA_1]);
               if(ATRSL1BUF.ATRSLUpper[LA_1]!=0 && ATRSL1BUF.ATRSLUpper[LA_2]!=0)
                  OBJECT_ATRSLBUFLINE("ATRSLBUF" + " " + "atrsl_slup" + "_" + (string)ATRSLBUF_count,ATRSL1BUF.ATRSLUpper[LA_1],"atrsl_slup",IndSidecolor,3, TIME_PREV1, TIME_PREV2, ATRSL1BUF.ATRSLUpper[LA_2], ATRSL1BUF.ATRSLUpper[LA_1]);
               if(ATRSL1BUF.ATRSLLower[LA_1]!=0 && ATRSL1BUF.ATRSLLower[LA_2]!=0)
                  OBJECT_ATRSLBUFLINE("ATRSLBUF" + " " + "atrsl_sldn" + "_" + (string)ATRSLBUF_count,ATRSL1BUF.ATRSLLower[LA_1],"atrsl_sldn",IndSidecolor,3, TIME_PREV1, TIME_PREV2, ATRSL1BUF.ATRSLLower[LA_2], ATRSL1BUF.ATRSLLower[LA_1]);
               ATRSLBUF_count+=1;
            }

            if(Show_plot && r==1)
            {
               // perform  draw labels
               if(TRADE_comment != "")
               {
                  DRAW_LABEL(TRADE_comment, TIME_CURRENT, close_prices[LA_1], LightCyan, 9, 2, 0, ANCHOR_LEFT, BB_datas[TF2arraynum(_Period)]);
               }
            }
         }
      }
            
      print_BBTFImpact(debug_info, BBTFImpact, close_prices, high_prices, low_prices);
      if(tradeInfo != "" && debug_info) Print("[TRADEINFO] " + tradeInfo);
      if(ATRSL1BUF.log != "" && debug_info) print_inner_1bufATRSL(ATRSL1BUF);
      // if(orderinfo != "" && debug_info) Print("[ORDERINFO]" + orderinfo);
   }
   DEINIT=false;
   PREV_BUYS=BUYS;
   PREV_SELLS=SELLS;
   LAST_BID    = Bid;
}

void TOTAL_VALUE(double &PROFIT_BUY,double &LOTS_BUY,double &PROFIT_SELL,double &LOTS_SELL, int &OPEN_BUY_TICKETNUM, int &OPEN_SELL_TICKETNUM, int MAGIC=-1)
  {
   PROFIT_BUY=LOTS_BUY=PROFIT_SELL=LOTS_SELL=0;

   for(int I=0; I<OrdersTotal(); I++)
     {
      if(OrderSelect(I,SELECT_BY_POS,MODE_TRADES))
      // if(OrderSelect(I))
        {
         if(OrderSymbol()==_Symbol && (OrderMagicNumber()==MAGIC || MAGIC==-1))
           {
            if(OrderType()==OP_BUY)
              {
               PROFIT_BUY+=NormalizeDouble(OrderProfit()+OrderSwap()+OrderCommission(),2);
               LOTS_BUY+=OrderLots();
               OPEN_BUY_TICKETNUM=OrderTicket();
              
              }
            if(OrderType()==OP_SELL)
              {
               PROFIT_SELL+=NormalizeDouble(OrderProfit()+OrderSwap()+OrderCommission(),2);
               LOTS_SELL+=OrderLots();
               OPEN_SELL_TICKETNUM=OrderTicket();
              }
           }
        }
     }
   return;
  }

void ORDERS_CLOSE(int CMD = -1,int TICKET = -1,double ORDER_LOTS=-1, string TRADE_INFO="")
  {
   string ORDER_CLOSE_info = "";
   string CMD2string = "";
   double corder_profit = 0.0;
   double corder_last_profit = 0.0;
   double corder_swap = 0.0;
   double corder_comm = 0.0;
   double corder_fee = 0.0;
   double corder_price = 0.0;
   int corder_DealsTotal = 0;
   datetime corder_open_time = 0;
   int corder_open_type = -1;
   double corder_open_volume = 0.0;
   double corder_open_price = 0.0;
   ulong LTicket = 0;
   int deal_entry = -1;
   int max_attempts = 10;
   int attempts = 0;
   long deal_type;
   for(int i=OrdersTotal()-1; i>=0; i--)
   {
      if(OrderSelect(i,SELECT_BY_POS,MODE_TRADES))
      {
         if(OrderSymbol()==_Symbol)
         {
            if(OrderType()==CMD || CMD==-1)
            {
               //  ORDER_CLOSE_info += ", OrderType:" + CMD;
                if(CMD == 0)
                  CMD2string = "BUY";
               else
                  CMD2string = "SELL";
               if((OrderTicket()==TICKET || TICKET==-1))
               {
                  // When TICKET==-1 (close-all), derive OPEN_* from the selected order, not history
                  if(TICKET == -1)
                  {
                     corder_open_time = OrderOpenTime();
                     corder_open_type = (int)OrderType();
                     corder_open_volume = OrderLots();
                     corder_open_price = OrderOpenPrice();
                  }
                  else
                  {
                     corder_open_time = HistoryDealGetInteger(TICKET, DEAL_TIME);
                     corder_open_type = HistoryDealGetInteger(TICKET, DEAL_TYPE);
                     corder_open_volume = HistoryDealGetDouble(TICKET, DEAL_VOLUME);
                     corder_open_price = HistoryDealGetDouble(TICKET, DEAL_PRICE); // <-- actual dealt price
                  }
                  ORDER_CLOSE_info += ", OPEN_TICKET:" + TICKET;
                  ORDER_CLOSE_info += ", OPEN_Type:" + (corder_open_type == DEAL_TYPE_SELL ? "SELL" : "BUY");
                  ORDER_CLOSE_info += ", OPEN_LOTS:" + corder_open_volume;
                  ORDER_CLOSE_info += ", OPEN_PRICE:" + corder_open_price;
                  ORDER_CLOSE_info += ", OPEN_TIME:" + corder_open_time;


                  if((OrderMagicNumber()==MAGIC_NUMBER || MAGIC_NUMBER==-1))
                  {
                     // ORDER_CLOSE_info += ", ORDER_LOTS:" + ORDER_LOTS;

                     if(!OrderClose(OrderTicket(),
                                    (ORDER_LOTS==-1 ? OrderLots() : ORDER_LOTS),
                                    OrderClosePrice(),
                                    0,
                                    clrNONE))
                     {
                        Print(__FUNCTION__," ",__LINE__," ERROR: ",GetLastError());
                        continue;  // try next order - do NOT return (orphan-freeze bug)
                     }

                     // Refresh history after close
                     HistorySelect(0, TimeCurrent());
                     corder_DealsTotal = HistoryDealsTotal();
                     LTicket = HistoryDealGetTicket(corder_DealsTotal-1);
                     deal_entry = HistoryDealGetInteger(LTicket, DEAL_ENTRY);

                     // Wait until we get a DEAL_ENTRY_OUT (close deal)
                     while(attempts < max_attempts && deal_entry != DEAL_ENTRY_OUT)
                     {
                        if(MQLInfoInteger(MQL_TESTER))
                           // In tester, history is synchronous - no need to sleep/wait
                           ;
                        else
                           Sleep(100);
                        HistorySelect(0, TimeCurrent());
                        corder_DealsTotal = HistoryDealsTotal();
                        LTicket = HistoryDealGetTicket(corder_DealsTotal-1);
                        deal_entry = HistoryDealGetInteger(LTicket, DEAL_ENTRY);
                        attempts++;
                     }
                     if(deal_entry != DEAL_ENTRY_OUT)
                     {
                        Print(__FUNCTION__, " WARNING: DEAL_ENTRY_OUT not received within ", max_attempts, " attempts");
                     }
                     int deal_type = HistoryDealGetInteger(LTicket, DEAL_TYPE);
                     double deal_volume = HistoryDealGetDouble(LTicket, DEAL_VOLUME);
                     double corder_profit   = HistoryDealGetDouble(LTicket, DEAL_PROFIT);
                     double corder_swap     = HistoryDealGetDouble(LTicket, DEAL_SWAP);
                     double corder_comm     = HistoryDealGetDouble(LTicket, DEAL_COMMISSION);
                     double corder_fee      = HistoryDealGetDouble(LTicket, DEAL_FEE);
                     double corder_price    = HistoryDealGetDouble(LTicket, DEAL_PRICE); // <-- actual dealt price
                     ORDER_CLOSE_info += ", CLOSED_TICKET:" + LTicket;
                     ORDER_CLOSE_info += ", CLOSED_TYPE:" + (deal_type == DEAL_TYPE_SELL ? "SELL" : "BUY");
                     ORDER_CLOSE_info += ", CLOSED_LOT:" + deal_volume;
                     ORDER_CLOSE_info += ", CLOSED_PRICE:" + DoubleToString(corder_price, _Digits);
                     ORDER_CLOSE_info += ", PROFIT:" + corder_profit;
                     ORDER_CLOSE_info += ", SWAP:" + corder_swap;
                     ORDER_CLOSE_info += ", COMMISION:" + corder_comm;
                     ORDER_CLOSE_info += ", FEE:" + corder_fee;

                     // Update totals
                     double corder_last_profit = TOTAL_PROFIT;
                     TOTAL_PROFIT = TOTAL_PROFIT + NormalizeDouble(corder_profit,2);
                     TOTAL_SWAP   = TOTAL_SWAP + corder_swap;

                     ORDER_CLOSE_info += ", TOTAL_PROFIT:" + TOTAL_PROFIT;
                     ORDER_CLOSE_info += ", TOTAL_SWAP:" + TOTAL_SWAP;
                     ORDER_CLOSE_info += ", LAST_PROFIT:" + corder_last_profit;

                     if(ORDER_CLOSE_info != "")
                        Print(" [NEW_ORDER_CLOSE], TradeAct:[" +TRADE_INFO+"]" + ORDER_CLOSE_info);
                  }
               }
            }
         }
      }
   }
}

void COUNT_ORDERS(int &BUY,int &SELL,int &BUYLIMIT,int &SELLLIMIT,int &BUYSTOP,int &SELLSTOP, int MAGIC=-1)
  {
   BUY=SELL=BUYLIMIT=SELLLIMIT=BUYSTOP=SELLSTOP=0;

   for(int I=0; I<OrdersTotal(); I++)
   {

      if(OrderSelect(I,SELECT_BY_POS,MODE_TRADES))
      {
         if(OrderSymbol()==_Symbol)
         {
            if((OrderMagicNumber()==MAGIC || MAGIC==-1))
            {
               switch(OrderType())
               {
               case OP_BUY:
                  BUY++;
                  break;
               case OP_SELL:
                  SELL++;
                  break;
               case OP_BUYLIMIT:
                  BUYLIMIT++;
                  break;
               case OP_SELLLIMIT:
                  SELLLIMIT++;
                  break;
               case OP_BUYSTOP:
                  BUYSTOP++;
                  break;
               case OP_SELLSTOP:
                  SELLSTOP++;
                  break;
               }
            }
         }
      }
   }
   return;
  }

void DRAW_LABEL(string Label, datetime curtime, double curval, color BBcolor, int FontSize, int ArrowWidth, int Tangle, int Tanchor, BB_MTF_Data_struct &BBTF_Data)
{
   string LabelName = "";
   string ArrowName = "";
   ENUM_OBJECT ArrowType = -1;
   int tfontsize = FontSize;

   int TextAnchor = 0;
   int ArrowAnchor = 0;
   
   Tanchor = ANCHOR_LEFT;
   // ArrowAnchor = ANCHOR_TOP;
   ArrowType = OBJ_ARROW_DOWN;

   LabelName = IndicatorName + "-" + TFTMigrate(BBTF_Data.BB_Ind_TIMEFRAME) + "-STAGE-LBL-" + Label + "-" + IntegerToString(curtime);
    
    ObjectCreate(0, LabelName, OBJ_TEXT, 0, curtime, curval);
    ObjectSetDouble(0, LabelName, OBJPROP_ANGLE, Tangle);
    ObjectSetInteger(0, LabelName, OBJPROP_ANCHOR, Tanchor);
    ObjectSetInteger(0, LabelName, OBJPROP_BACK, false);
    ObjectSetInteger(0, LabelName, OBJPROP_HIDDEN, true);
    ObjectSetInteger(0, LabelName, OBJPROP_FONTSIZE, tfontsize);
    ObjectSetString(0, LabelName, OBJPROP_FONT, Font);
    ObjectSetString(0, LabelName, OBJPROP_TEXT, Label);
    ObjectSetInteger(0, LabelName, OBJPROP_SELECTABLE, false);
    ObjectSetInteger(0, LabelName, OBJPROP_COLOR, BBcolor);
}

void ORDER_SEND(ENUM_ORDER_TYPE CMD, double LOTS, string COMMENT, int MAGIC, 
                string TRADE_INFO="", double SL=0.0, double TP=0.0)
{
   string ORDER_SEND_info = "";
   string CMD2sting = "";

   if(OrdersTotal() < AccountInfoInteger(ACCOUNT_LIMIT_ORDERS) || 
      AccountInfoInteger(ACCOUNT_LIMIT_ORDERS) == 0)
   {
      // ── LOT NORMALIZATION ─────────────────────────────────────────
      if(LOTS < SymbolInfoDouble(NULL, SYMBOL_VOLUME_MIN))
         LOTS = SymbolInfoDouble(NULL, SYMBOL_VOLUME_MIN);
      if(LOTS > SymbolInfoDouble(NULL, SYMBOL_VOLUME_MAX))
         LOTS = SymbolInfoDouble(NULL, SYMBOL_VOLUME_MAX);
      LOTS = MathMin(
               MathMax(
                  MathRound(LOTS / SymbolInfoDouble(NULL, SYMBOL_VOLUME_STEP)) 
                  * SymbolInfoDouble(NULL, SYMBOL_VOLUME_STEP),
                  SymbolInfoDouble(NULL, SYMBOL_VOLUME_MIN)),
               SymbolInfoDouble(NULL, SYMBOL_VOLUME_MAX));

      // ── MARGIN CHECK ──────────────────────────────────────────────
      double freeMargin     = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      double marginRequired = SymbolInfoDouble(_Symbol, SYMBOL_MARGIN_INITIAL);
      double minVolume      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);

      CMD2sting = (CMD == 0) ? "BUY" : "SELL";

      if((freeMargin <= marginRequired * LOTS + minVolume) ||
         (AccountInfoDouble(ACCOUNT_MARGIN_FREE) <= marginRequired * minVolume))
      {
         Print(__FUNCTION__, " ", __LINE__, " MARGIN_ERROR: ", GetLastError());
         return;  // no sleep needed - not mid-loop
      }

      if((ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(NULL, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_FULL)
         return;

      // ── SL NORMALIZATION ──────────────────────────────────────────
      // Normalize SL to broker's digit precision
      double normalizedSL = 0.0;
      double normalizedTP = 0.0;
      int    digits       = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      double point        = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      double stopLevel    = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
      double entryPrice   = (CMD == OP_BUY) 
                              ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                              : SymbolInfoDouble(_Symbol, SYMBOL_BID);

      if(SL > 0.0) {
         normalizedSL = NormalizeDouble(SL, digits);

         // Validate SL is beyond minimum stop level from entry
         double slDistance = MathAbs(entryPrice - normalizedSL);
         if(slDistance < stopLevel) {
            // Push SL to at least minimum stop level
            normalizedSL = (CMD == OP_BUY) 
                             ? NormalizeDouble(entryPrice - stopLevel, digits)
                             : NormalizeDouble(entryPrice + stopLevel, digits);
            if(debug_info)
               Print("[ORDER_SEND] SL adjusted to min stop level: ", normalizedSL);
         }
      }

      if(TP > 0.0)
         normalizedTP = NormalizeDouble(TP, digits);

      // ── ORDER SEND ────────────────────────────────────────────────
      ulong ticket = OrderSend(_Symbol,
                               CMD,
                               LOTS,
                               entryPrice,
                               0,
                               0, 0,          // send with 0,0 first
                               COMMENT + "-" + TRADE_INFO,
                               MAGIC,
                               0,
                               clrNONE);

      if(ticket == 0) {
         Print(__FUNCTION__, " ", __LINE__, " SEND_ERROR: ", GetLastError());
         Sleep(1000);
         return;
      }

      // ── SL/TP MODIFY AFTER OPEN ───────────────────────────────────
      // Must select the order before modifying
      if((normalizedSL > 0.0 || normalizedTP > 0.0) && OrderSelect((int)ticket, SELECT_BY_TICKET))
      {
         double openPrice = OrderOpenPrice();

         // Re-validate SL after actual fill price is known
         if(normalizedSL > 0.0) {
            double actualDist = MathAbs(openPrice - normalizedSL);
            if(actualDist < stopLevel) {
               normalizedSL = (CMD == OP_BUY)
                                ? NormalizeDouble(openPrice - stopLevel, digits)
                                : NormalizeDouble(openPrice + stopLevel, digits);
            }
         }

         bool modified = OrderModify(
                            (int)ticket,
                            openPrice,
                            normalizedSL,
                            normalizedTP,
                            0,
                            clrNONE);

         if(!modified) {
            Print(__FUNCTION__, " ", __LINE__, 
                  " MODIFY_ERROR: ", GetLastError(),
                  " SL:", normalizedSL, " TP:", normalizedTP);
         }
         else {
            ORDER_SEND_info += ", SL_SET:" + DoubleToString(normalizedSL, digits);
            if(normalizedTP > 0.0)
               ORDER_SEND_info += ", TP_SET:" + DoubleToString(normalizedTP, digits);
         }
      }

      // ── DEAL HISTORY LOG ──────────────────────────────────────────
      if(HistorySelect(0, TimeCurrent()))
      {
         ulong deal_ticket = HistoryDealGetTicket(HistoryDealsTotal() - 1);
         if(HistoryDealSelect(deal_ticket))
         {
            int    deal_entry  = HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
            int    deal_type   = HistoryDealGetInteger(deal_ticket, DEAL_TYPE);
            double deal_volume = HistoryDealGetDouble(deal_ticket, DEAL_VOLUME);
            double deal_price  = HistoryDealGetDouble(deal_ticket, DEAL_PRICE);

            ORDER_SEND_info += ", OPEN_TICKET:" + ticket;
            ORDER_SEND_info += ", OPEN_TYPE:"   + (deal_type == DEAL_TYPE_SELL ? "SELL" : "BUY");
            ORDER_SEND_info += ", OPEN_LOTS:"   + DoubleToString(deal_volume, 2);
            ORDER_SEND_info += ", DEAL_PRICE:"  + DoubleToString(deal_price, digits);
         }
      }
      ORDER_SEND_info += ", FREEMARGIN:"     + DoubleToString(freeMargin, 2);
      ORDER_SEND_info += ", MARGINREQUIRED:" + DoubleToString(marginRequired, 2);
   }

   if(ORDER_SEND_info != "" && debug_info)
      Print("[NEW_ORDER_OPEN], TradeAct:[" + TRADE_INFO + "]" + ORDER_SEND_info);
}

void OPENED_VALUES(double &PRICE_BUY,double &LOTS_BUY,double &PRICE_SELL,double &LOTS_SELL)
{
   string ORDER_OPEN_info = "";
   PRICE_BUY=LOTS_BUY=PRICE_SELL=LOTS_SELL=0;
   int OLD_TICKET=0,TICKET=0;

   for(int i=0; i<OrdersTotal(); i++)
   {
      ORDER_OPEN_info = "";
      if(OrderSelect(i,SELECT_BY_POS,MODE_TRADES))
      {
         ORDER_OPEN_info += ", OrderSelect:" + i;
         if(OrderSymbol()==_Symbol)
         {
            ORDER_OPEN_info += ", Symbol:" + _Symbol;
            if((OrderMagicNumber()==MAGIC_NUMBER || MAGIC_NUMBER==-1))
            {
               ORDER_OPEN_info += ", MagicNumber:" + MAGIC_NUMBER;
               // get ticket number of the currently selected order.
               OLD_TICKET=OrderTicket();
                  ORDER_OPEN_info += ", OLD_TICKET:" + OLD_TICKET;
                  ORDER_OPEN_info += ", TICKET:" + TICKET;
               // TICKET = prev OLD_TICKET, OLD_TICKET will be latest TICKET
               if(OLD_TICKET>TICKET)
               {
                  if(OrderType()==OP_BUY)
                  {
                     PRICE_BUY=OrderOpenPrice();
                     LOTS_BUY=OrderLots();
                  }
                  if(OrderType()==OP_SELL)
                  {
                     PRICE_SELL=OrderOpenPrice();
                     LOTS_SELL=OrderLots();
                  }
                  TICKET=OLD_TICKET;
               }
            }
         }
      }
   }
   return;
}

double LOT_CALCULATE(double RISK,double SL,double BALANCE,double BALANCE_LOT)
{
   double LOT=0;
   // risk management
   if(Lot_Management == 0){
      if(RISK_PER_TRADE>0)
      {
         // LOT = 1000 * 1/100
         LOT = NormalizeDouble(((AccountInfoDouble(ACCOUNT_BALANCE)*RISK/100.0)/SL)/(TICKVALUE!=0?TICKVALUE:1),2);
         LOT = NormalizeDouble(LOT/MarketInfo(_Symbol,MODE_LOTSTEP),2) * MarketInfo(_Symbol,MODE_LOTSTEP);
      }
      else
      {
         Print("RISK_PER_TRADE cannot be less than 0 when risk Management!!");
         Print(__FUNCTION__, " ", __LINE__, " ERROR: ", GetLastError());
         return -1;
      }
   }
   else if(Lot_Management == 2){// average balance
      if(FROM_BALANCE>0)
         LOT=AccountBalance()/BALANCE*BALANCE_LOT;
      else{
        Print("FROM_BALANCE cannot be less than 0 for average lot!!");
        Print(__FUNCTION__, " ", __LINE__, " ERROR: ", GetLastError());
        // Sleep(1000);
        return -1;
      }
   }
    else if(Lot_Management == 1){/// fix
        if(VOLUME>0)
            LOT=VOLUME;
        else{
            Print("LOT cannot be less than 0 for average lot!!");
            Print(__FUNCTION__, " ", __LINE__, " ERROR: ", GetLastError());
            // Sleep(1000);
            return -1;
        }
    }

   return(LOT);
}

void DetectNewBar(ENUM_TIMEFRAMES period_time)
{
   static datetime lastBarTime = 0;
   datetime currentBarTime = iTime(Symbol(), period_time, 0);

   if (currentBarTime != lastBarTime)
   {
       IsNewBar = true;
       lastBarTime = currentBarTime;
   }
   else
   {
       IsNewBar = false;
   }
}

void DEINIT_ATRSLBUFLINE()
{
   Print("ATRSLBUF from ObjectsTotal:" + ObjectsTotal(0, 0,-1));
   for(int i=ObjectsTotal(0, 0,-1)-1; i>=0; i--)
   {
      if(StringFind(ObjectName(0,i,-1,-1),"ATRSLBUF")>=0){
        ObjectDelete(0,ObjectName(0,i,-1,-1));
      }
   }
}

void OBJECT_ATRSLBUFLINE(string NAME,double _PRICE,string TEXT,color CLR,int STYLE, datetime curtime, datetime prevtime, double prevval, double curval)
{
   if(ObjectFind(0,NAME)<0)
     {
      // ObjectCreate(0,NAME,OBJ_HLINE,0,0,0);
      ObjectCreate(0, NAME, OBJ_TREND, 0, prevtime, prevval, curtime, curval);
      ObjectSetInteger(0,NAME,OBJPROP_COLOR,CLR);
      ObjectSetInteger(0,NAME,OBJPROP_STYLE,STYLE_SOLID);
      ObjectSetInteger(0,NAME,OBJPROP_WIDTH,3);
      ObjectSetInteger(0,NAME,OBJPROP_BACK,true);
      ObjectSetInteger(0,NAME,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,NAME,OBJPROP_SELECTED,false);
      ObjectSetInteger(0,NAME,OBJPROP_HIDDEN,true);
      ObjectSetInteger(0,NAME,OBJPROP_ZORDER,0);
      ObjectSet(NAME,OBJPROP_READONLY,false);
      ObjectSetText(NAME,TEXT,0, NULL, clrNONE);
     }
   else
     {
      ObjectSetDouble(0,NAME,OBJPROP_PRICE,0,_PRICE);
      ObjectSetString(0,NAME,OBJPROP_TOOLTIP,TEXT);
      ObjectSetInteger(0,NAME,OBJPROP_COLOR,CLR);
     }

   ChartRedraw();
}

void print_inner_1bufATRSL(ATRSLBUF_struct &ATRSL1BUF)
{
   int array_size = ArraySize(ATRSL1BUF.ATRLV);
   ATRSL1BUF.log += ", Trend:[";
   for(int a=array_size-1; a != 0; a--){
      ATRSL1BUF.log += (string)NormalizeDouble(ATRSL1BUF.ATRTrend[a], Digits) + ",";
   }
   ATRSL1BUF.log += "]";

   ATRSL1BUF.log += ", LV:[";
   for(int a=array_size-1; a != 0; a--){
      ATRSL1BUF.log += (string)NormalizeDouble(ATRSL1BUF.ATRLV[a], Digits) + ",";
   }
   ATRSL1BUF.log += "]";

   ATRSL1BUF.log += ", Upper:[";
   for(int a=array_size-1; a != 0; a--){
      ATRSL1BUF.log += (string)NormalizeDouble(ATRSL1BUF.ATRSLUpper[a], Digits) + ",";
   }
   ATRSL1BUF.log += "]";

   ATRSL1BUF.log += ", Lower:[";
   for(int a=array_size-1; a != 0; a--){
      ATRSL1BUF.log += (string)NormalizeDouble(ATRSL1BUF.ATRSLLower[a], Digits) + ",";
   }
   ATRSL1BUF.log += "]";

   ATRSL1BUF.log += ", SLMid:[";
   for(int a=array_size-1; a != 0; a--){
      ATRSL1BUF.log += (string)NormalizeDouble(ATRSL1BUF.ATRSLMid[a], Digits) + ",";
   }
   ATRSL1BUF.log += "]";

   ATRSL1BUF.log += ", Val:[";
   for(int a=array_size-1; a != 0; a--){
      ATRSL1BUF.log += (string)NormalizeDouble(ATRSL1BUF.ATRVal[a], Digits) + ",";
   }
   ATRSL1BUF.log += "]";

   Print("[ATRSL1buf]" + ATRSL1BUF.log);
}

void print_BBdata(BB_MTF_Data_struct &BB_data, BB_MTF_Impact_struct &BBTFImpact, string &stage_debug_log, string &midtrend_debug_log, bool &debug_info, int arraynum)
{
   string BB_strategy_info = "";
   string str_stage = "";
   update_stages2_TFImpact(BBTFImpact, BB_data, str_stage);
   if(debug_info && arraynum >= 0)
   {
      if(stage_debug_log != "") BB_strategy_info += "(" + stage_debug_log + ")";
      if(midtrend_debug_log != "") BB_strategy_info += "(" + midtrend_debug_log + ")";
      BB_strategy_info += "[" + arraynum_2_string(arraynum) + "]";
      if(BB_data.first_stage == true) BB_strategy_info += ", first_stage_" + arraynum_2_string(arraynum) + ":[1]";

      BB_strategy_info += ", W_stage_" + arraynum_2_string(arraynum) + ":(" + str_stage + ")[" + BB_data.BBW_stage[LA] + ", ";
      BB_strategy_info += BB_data.BBW_stage[LA_1] + ", ";
      BB_strategy_info += BB_data.BBW_stage[LA_2];
      BB_strategy_info += "], ";

      BB_strategy_info += "diffMid_Trend_" + arraynum_2_string(arraynum) + ":[" + NormalizeDouble(BB_data.BB_diffMid_Trend[LA], Digits)  + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BB_diffMid_Trend[LA_1], Digits)  + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BB_diffMid_Trend[LA_2], Digits);
      BB_strategy_info += "], ";
      
      BB_strategy_info += "BBUpDn_" + arraynum_2_string(arraynum) + ":[" + BB_data.BBUpDn_state[LA] + ", ";
      BB_strategy_info += BB_data.BBUpDn_state[LA_1] + ", ";
      BB_strategy_info += BB_data.BBUpDn_state[LA_2];
      BB_strategy_info += "], ";

      BB_strategy_info += "trend_" + arraynum_2_string(arraynum) + ":[" + BB_data.BB_trend[LA] + ", ";
      BB_strategy_info += BB_data.BB_trend[LA_1] + ", ";
      BB_strategy_info += BB_data.BB_trend[LA_2] + ", ";
      BB_strategy_info += "], ";

      BB_strategy_info += "prev_trend_" + arraynum_2_string(arraynum) + ":" + BB_data.prev_BB_trend;
      BB_strategy_info += ", ";

      BB_strategy_info += "diffMid_"+ arraynum_2_string(arraynum) +":[" + NormalizeDouble(BB_data.BB_diffMid[LA], Digits) + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BB_diffMid[LA_1], Digits) + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BB_diffMid[LA_2], Digits);
      BB_strategy_info += "], ";

      BB_strategy_info += "diffBBW_"+ arraynum_2_string(arraynum) +":[" + NormalizeDouble(BB_data.BB_diffBBW[LA], Digits) + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BB_diffBBW[LA_1], Digits) + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BB_diffBBW[LA_2], Digits);
      BB_strategy_info += "], ";

      BB_strategy_info += "WLV_"+ arraynum_2_string(arraynum) +":[" + NormalizeDouble(BB_data.BBWLV[LA], Digits) + ",";
      BB_strategy_info += NormalizeDouble(BB_data.BBWLV[LA_1], Digits) + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BBWLV[LA_2], Digits);
      BB_strategy_info += "], ";

      BB_strategy_info += "MidLV_"+ arraynum_2_string(arraynum) +":[" + NormalizeDouble(BB_data.BBMidLV[LA], Digits) + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BBMidLV[LA_1], Digits) + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BBMidLV[LA_2], Digits);
      BB_strategy_info += "], ";

      BB_strategy_info += "UppLV_" + arraynum_2_string(arraynum) +":[" + NormalizeDouble(BB_data.BBUppLV[LA], Digits) + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BBUppLV[LA_1], Digits) + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BBUppLV[LA_2], Digits);
      BB_strategy_info += "], ";

      BB_strategy_info += "LowLV_" + arraynum_2_string(arraynum) +":[" + NormalizeDouble(BB_data.BBLowLV[LA], Digits) + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BBLowLV[LA_1], Digits) + ", ";
      BB_strategy_info += NormalizeDouble(BB_data.BBLowLV[LA_2], Digits);
      BB_strategy_info += "], ";

      if(arraynum_2_string(arraynum) == "M5" || arraynum_2_string(arraynum) == "M15")
      {
         BB_strategy_info += "close_" + arraynum_2_string(arraynum)+":[" + NormalizeDouble(close_prices[LA], Digits) + ", ";
         BB_strategy_info += NormalizeDouble(close_prices[LA_1], Digits) + ", ";
         BB_strategy_info += NormalizeDouble(close_prices[LA_2], Digits);
         BB_strategy_info += "], ";

         BB_strategy_info += "high_" + arraynum_2_string(arraynum)+":[" + NormalizeDouble(high_prices[LA], Digits) + ", ";
         BB_strategy_info += NormalizeDouble(high_prices[LA_1], Digits) + ", ";
         BB_strategy_info += NormalizeDouble(high_prices[LA_2], Digits);
         BB_strategy_info += "], ";

         BB_strategy_info += "low_" + arraynum_2_string(arraynum)+":[" + NormalizeDouble(low_prices[LA], Digits) + ", ";
         BB_strategy_info += NormalizeDouble(low_prices[LA_1], Digits) + ", ";
         BB_strategy_info += NormalizeDouble(low_prices[LA_2], Digits);
         BB_strategy_info += "], ";
      }
      
   }
   if(BB_strategy_info != "" && debug_info) Print(BB_strategy_info);
}

void print_BBTFImpact(bool debug_info, BB_MTF_Impact_struct &BBTFImpact, double &close_price[], double &high_price[], double &low_price[])
{
   string STRATEGY_info = "";
   string BB_HTF_Drive_LTF_Sideway_info = "";
   string BB_LTF_Drive_HTF_Fly_info = "";
   string BB_Midline_cross_info = "";
   string BBline_seq_touch_infos = "";
   string BBline_seq_touch_check_infos = "";
   string BBline_seq_cross_info = "";
   // string close_info = "";
   // string high_info = "";
   // string low_info = "";
   // string BB_CloseDist2BBLines_info = "";
   string untouch_val_info = "";
   // string Price_Act_info = "";
   string BB_midline_Cluster_info = "";
   int TFnum = TF2arraynum(_Period);

   // if(BBTFImpact.BB_midline_Cluster[0][LA] != 0)
   // {
   //    BB_midline_Cluster_info += NormalizeDouble(BBTFImpact.BB_midline_Cluster[0][LA], 2) + ", " + NormalizeDouble(BBTFImpact.BB_midline_Cluster[1][LA], 2) + ", " + NormalizeDouble(BBTFImpact.BB_midline_Cluster[2][LA], 2) + ", " + NormalizeDouble(BBTFImpact.BB_midline_Cluster[3][LA], 2);
      
   //    if(BB_midline_Cluster_info != "")
   //    {
   //       STRATEGY_info += "midline_Cluster:[" + BB_midline_Cluster_info + "], ";
   //    }
   // }
   //--- All seven midline pairs. Loop rather than a fixed list so adding a pair to
   //--- BBDatas_Midline_Cluster shows up here without a second edit.
   //---   0 M15+M5   1 M15+M30   2 M15+H1   3 M30+H1
   //---   4 M15+H4   5 M30+H4    6 H1+H4
   if(BBTFImpact.BB_midline_Cluster[0][LA] != 0)
   {
      for(int ci = 0; ci < ArrayRange(BBTFImpact.BB_midline_Cluster, 0); ci++)
      {
         if(ci > 0) BB_midline_Cluster_info += ", ";
         BB_midline_Cluster_info +=
            DoubleToString(BBTFImpact.BB_midline_Cluster[ci][LA], 2);
      }

      if(BB_midline_Cluster_info != "")
      {
         STRATEGY_info += "midline_Cluster:[" + BB_midline_Cluster_info + "], ";
      }
   }

   if( ArraySize(BB_datas) > 0)
   {
      for(int j=TFnum; j<ArraySize(BB_datas); j++)
      {
         if(BBline_seq_touch_infos != "")
         {
            BBline_seq_touch_infos += ", ";
         }
         BBline_seq_touch_infos += arraynum_2_string(j) + "_" + BB_datas[j].BBline_seq_touch[LA] + "-" + BB_datas[j].BBline_seq_touch[LA_1] + "," + BB_datas[j].BBline_seq_touch[LA_2];
      }
      if(BBline_seq_touch_infos != "")
      {
         STRATEGY_info += "line_seq_touch:[" + BBline_seq_touch_infos + "], ";
      }
   }

   if( ArraySize(BB_datas) > 0)
   {
      for(int j=TFnum; j<ArraySize(BB_datas); j++)
      {
         if(BBline_seq_cross_info != "")
         {
            BBline_seq_cross_info += ", ";
         }
         BBline_seq_cross_info += arraynum_2_string(j) + "_" + BB_datas[j].BBline_seq_cross[LA] + "-" +  BB_datas[j].BBline_seq_cross[LA_1] + "," +  BB_datas[j].BBline_seq_cross[LA_2];
      }
      if(BBline_seq_cross_info != "")
      {
         STRATEGY_info += "line_seq_cross:[" + BBline_seq_cross_info + "], ";
      }
   }

   if( ArraySize(BBTFImpact.untouch_val) > 0)
   {
      for(int j=TFnum; j<ArraySize(BBTFImpact.untouch_val); j++)
      {
         if(untouch_val_info != "")
         {
            untouch_val_info += ", ";
         }
         untouch_val_info += arraynum_2_string(j) + "_" + BBTFImpact.untouch_val[j] + "-" + BBTFImpact.untouch_prev_val[j];

      }
      if(untouch_val_info != "")
      {
         STRATEGY_info += "untouch_val:[" + untouch_val_info + "], ";
      }
   }
   
   if( ArraySize(BB_datas) > 0)
   {
      for(int j=TFnum; j<ArraySize(BB_datas); j++)
      {
         if(BB_Midline_cross_info != "")
         {
            BB_Midline_cross_info += ", ";
         }
         BB_Midline_cross_info += arraynum_2_string(j) + "_" + BB_datas[j].BB_Midline_cross[LA] + "-" + BB_datas[j].BB_Midline_cross[LA_1];

      }
      if(BB_Midline_cross_info != "")
      {
         STRATEGY_info += "Midline_cross:[" + BB_Midline_cross_info + "]";
      }
   }

   if( ArraySize(BBTFImpact.BB_HTF_Drive_LTF_Sideway) > 0)
   {
      for(int j=TFnum; j<ArraySize(BBTFImpact.BB_HTF_Drive_LTF_Sideway); j++)
      {
         if(BBTFImpact.BB_HTF_Drive_LTF_Sideway[j])
         {
            if(BB_HTF_Drive_LTF_Sideway_info != "")
            {
               BB_HTF_Drive_LTF_Sideway_info += ", ";
            }
            BB_HTF_Drive_LTF_Sideway_info += arraynum_2_string(j) + "_" + BBTFImpact.BB_HTF_Drive_LTF_Sideway[j];
         }
      }
      if(BB_HTF_Drive_LTF_Sideway_info != "")
      {
         STRATEGY_info += "HTF_Drive_LTF_Sideway:[" + BB_HTF_Drive_LTF_Sideway_info + "], ";
      }
   }

   if( ArraySize(BBTFImpact.BB_LTF_Drive_HTF_Fly) > 0)
   {
      for(int j=TFnum; j<ArraySize(BBTFImpact.BB_LTF_Drive_HTF_Fly); j++)
      {
         if(BBTFImpact.BB_LTF_Drive_HTF_Fly[j])
         {
            if(BB_LTF_Drive_HTF_Fly_info != "")
            {
               BB_LTF_Drive_HTF_Fly_info += ", ";
            }
             BB_LTF_Drive_HTF_Fly_info += arraynum_2_string(j) + "_" + BBTFImpact.BB_LTF_Drive_HTF_Fly[j];
         }
      }
      if(BB_LTF_Drive_HTF_Fly_info != "")
      {
         STRATEGY_info += "LTF_Drive_HTF_Fly:[" + BB_LTF_Drive_HTF_Fly_info + "], ";
      }
   }
   if( debug_info) Print("[BBTFImpact] " + STRATEGY_info);
}

void print_orderinfo(bool debug_info, enum_mode MODE, double BUY_PROFIT, double BUY_LOTS, int OPEN_BUY_TICKET_NUM, int BUYS, double SELL_PROFIT, double SELL_LOTS, int OPEN_SELL_TICKET_NUM, int SELLS)
{
   string orderinfo = "";
   if(MODE < 3)
   {
      orderinfo += ", BUY_PROFIT:" + BUY_PROFIT;
      orderinfo += ", BUY_LOTS:" + BUY_LOTS;
      orderinfo += ", BUY_TICKET_NUM:" + OPEN_BUY_TICKET_NUM;
      orderinfo += ", BUYS:" + BUYS;
      orderinfo += ", SELL_PROFIT:" + SELL_PROFIT;
      orderinfo += ", SELL_LOTS:" + SELL_LOTS;
      orderinfo += ", SELL_TICKET_NUM:" + OPEN_SELL_TICKET_NUM;
      orderinfo += ", SELLS:" + SELLS;
      orderinfo += ", TOTALORDERS:" + OrdersTotal();
   }
   if(debug_info) Print("[ORDERINFO]" + orderinfo);
}

// Add this helper function (near DRAW_LABEL, ~line 943):
string CircledNum(int n)
{
   // 0-20  -> U+24EA, U+2460..U+2473 ;  21-30 -> U+3251..U+325A
   if(n == 0)              return ShortToString(0x24EA);
   if(n >= 1  && n <= 20)  return ShortToString((ushort)(0x2460 + (n - 1)));
   if(n >= 21 && n <= 30)  return ShortToString((ushort)(0x3251 + (n - 21)));
   return IntegerToString(n);   // fallback for out-of-range
}