import numpy as np
import pandas as pd

PRESETS={
"Quality Compounder":{"min_roe":15,"max_de":1,"min_fcf":0,"min_rev_cagr_5yr":10},
"Value Pick":{"max_pe":20,"max_pb":3,"max_de":2,"min_dividend_yield":1},
"Growth Accelerator":{"min_pat_cagr_5yr":20,"min_rev_cagr_5yr":15,"max_de":2},
"Dividend Champion":{"min_dividend_yield":2,"max_dividend_payout":80,"min_fcf":0},
"Debt-Free Blue Chip":{"max_de":0,"min_roe":12,"min_sales":5000},
"Turnaround Watch":{"min_rev_cagr_3yr":10,"min_fcf":0}}

def _num(s): return pd.to_numeric(s,errors="coerce")
def _yr(x):
    m=__import__("re").search(r"\d{4}",str(x))
    return int(m.group()) if m else np.nan
def cagr(x,ticker,n,col):
    x=x[x.company_id.astype(str).eq(str(ticker))].copy()
    x["_y"]=x.year.map(_yr); x[col]=_num(x[col])
    x=x.dropna(subset=["_y",col]).drop_duplicates("_y",keep="last")
    if x.empty:return np.nan
    y=int(x._y.max()); a=x[x._y.eq(y-n)][col]; b=x[x._y.eq(y)][col]
    if a.empty or b.empty or a.iloc[0]<=0 or b.iloc[0]<0:return np.nan
    return ((b.iloc[0]/a.iloc[0])**(1/n)-1)*100

def build_screener_universe(companies,ratios,pl,market):
    r=ratios.copy(); r["_y"]=r.year.map(_yr)
    r=r.dropna(subset=["_y"]).sort_values(["company_id","_y"]).drop_duplicates(["company_id","_y"],keep="last")
    latest=r.groupby("company_id",as_index=False).tail(1)
    rows=[]
    for t in companies.company_id.dropna().astype(str):
        rows.append({"company_id":t,
                     "revenue_cagr_3yr":cagr(pl,t,3,"sales"),
                     "revenue_cagr_5yr":cagr(pl,t,5,"sales"),
                     "pat_cagr_5yr":cagr(pl,t,5,"net_profit")})
    out=latest.merge(companies[["company_id","company_name","broad_sector","sub_sector"]],on="company_id",how="left")
    out=out.merge(pd.DataFrame(rows),on="company_id",how="left")
    if not market.empty:
        m=market.copy(); m["_y"]=_num(m.calendar_year)
        m=m.sort_values(["company_id","_y"]).groupby("company_id",as_index=False).tail(1)
        cols=[c for c in ["company_id","pe_ratio","pb_ratio","dividend_yield_pct","market_cap_crore"] if c in m]
        out=out.merge(m[cols],on="company_id",how="left")
    return out

def apply_filters(df,**f):
    out=df.copy()
    def ge(col,v):
        nonlocal out
        if v is not None and col in out:
            s=_num(out[col]); out=out[s.ge(float(v))|s.isna()]
    def le(col,v):
        nonlocal out
        if v is not None and col in out:
            s=_num(out[col]); out=out[s.le(float(v))|s.isna()]
    ge("return_on_equity_pct",f.get("min_roe")); ge("free_cash_flow_cr",f.get("min_fcf"))
    ge("revenue_cagr_5yr",f.get("min_rev_cagr_5yr")); ge("pat_cagr_5yr",f.get("min_pat_cagr_5yr"))
    ge("operating_profit_margin_pct",f.get("min_opm")); ge("dividend_yield_pct",f.get("min_dividend_yield"))
    ge("sales",f.get("min_sales")); ge("revenue_cagr_3yr",f.get("min_rev_cagr_3yr"))
    le("pe_ratio",f.get("max_pe")); le("pb_ratio",f.get("max_pb"))
    le("dividend_payout_ratio_pct",f.get("max_dividend_payout"))
    if f.get("max_de") is not None and "debt_to_equity" in out:
        de=_num(out.debt_to_equity)
        sec=out.broad_sector.astype(str).str.lower()
        fin=sec.str.contains("financial|bank|insurance|nbfc|finance|lending|credit")
        out=out[de.le(float(f["max_de"]))|de.isna()|fin]
    if f.get("min_icr") is not None and "interest_coverage" in out:
        icr=_num(out.interest_coverage); debtfree=_num(out.get("total_debt_cr",pd.Series(np.nan,index=out.index))).fillna(0).eq(0)
        out=out[icr.ge(float(f["min_icr"]))|icr.isna()|debtfree]
    score=pd.Series(50.0,index=out.index)
    for col,sign in [("return_on_equity_pct",1),("revenue_cagr_5yr",1),("pat_cagr_5yr",1),("debt_to_equity",-1)]:
        if col in out:
            s=_num(out[col]); lo,hi=s.quantile(.1),s.quantile(.9)
            if pd.notna(lo) and pd.notna(hi) and hi>lo:
                n=(s.clip(lo,hi)-lo)/(hi-lo)*100
                if sign<0:n=100-n
                score=n.fillna(50)
                out["composite_quality_score"]=score
    if "composite_quality_score" not in out: out["composite_quality_score"]=score
    return out.sort_values("composite_quality_score",ascending=False).reset_index(drop=True)
