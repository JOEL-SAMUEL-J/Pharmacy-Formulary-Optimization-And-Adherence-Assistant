"""Transparent review-priority heuristic; not a clinical risk model."""
from decimal import Decimal

LEVEL_ORDER={"none":0,"low":1,"moderate":2,"high":3}

def access_barriers(restrictions,indications,excluded=False):
    reasons=[];score=0
    if excluded: reasons.append("Drug is covered only as a supplemental excluded drug");score+=3
    if restrictions.get("prior_authorization"):
        reasons.append("Prior authorization required");score+=2
    if restrictions.get("step_therapy"):
        reasons.append("Step therapy required");score+=2
    if restrictions.get("quantity_limit"):
        amount=restrictions.get("quantity_limit_amount") or "unspecified amount"
        days=restrictions.get("quantity_limit_days") or "unspecified period"
        reasons.append(f"Quantity limit: {amount} per {days} days");score+=1
    if indications:
        reasons.append("Coverage depends on an approved indication");score+=1
    level="none" if score==0 else "low" if score==1 else "moderate" if score<=3 else "high"
    return {"level":level,"reasons":reasons}

def affordability_barriers(tier,deductible_applies,specialty_tier,channels):
    reasons=[];high=False
    if tier>=3: reasons.append(f"Tier {tier}")
    if deductible_applies: reasons.append("Deductible applies")
    if specialty_tier: reasons.append("Specialty-tier cost sharing");high=True
    offered=[channel for channel in channels.values() if channel["type"]!="not_offered"]
    for channel in offered:
        amount=Decimal(str(channel["amount"]))
        if channel["type"]=="coinsurance" and amount>=Decimal("0.25"): high=True
        if channel["type"]=="copay" and amount>=Decimal("100"): high=True
    if any(c["type"]=="coinsurance" for c in offered): reasons.append("Percentage-based coinsurance applies")
    elif any(Decimal(str(c["amount"]))>0 for c in offered): reasons.append("Plan-listed copay applies")
    if high: level="high"
    elif reasons: level="moderate" if deductible_applies or tier>=3 else "low"
    else: level="none"
    return {"level":level,"reasons":reasons}

def channel_opportunity(channels):
    offered={name:value for name,value in channels.items() if value["type"]!="not_offered"}
    if len(offered)<2: return {"level":"none","reasons":["Fewer than two pharmacy channels are offered"]}
    comparable={kind:{n:v for n,v in offered.items() if v["type"]==kind}
                for kind in ("copay","coinsurance")}
    reasons=[]
    for kind,values in comparable.items():
        if len(values)<2: continue
        amounts=[Decimal(str(v["amount"])) for v in values.values()]
        if max(amounts)>min(amounts):
            low=[n for n,v in values.items() if Decimal(str(v["amount"]))==min(amounts)]
            unit="$" if kind=="copay" else " percentage-point"
            difference=max(amounts)-min(amounts)
            shown=difference if kind=="copay" else difference*100
            reasons.append(f"Lower {kind} through {', '.join(low)} by {unit}{shown}")
    return {"level":"moderate" if reasons else "none",
            "reasons":reasons or ["No plan-listed cost difference across comparable offered channels"]}

def build_opportunity(restrictions,tier,deductible_applies,specialty_tier,
                      channels,indications,excluded=False):
    access=access_barriers(restrictions,indications,excluded)
    affordability=affordability_barriers(tier,deductible_applies,specialty_tier,channels)
    channel=channel_opportunity(channels)
    overall=max((access["level"],affordability["level"],channel["level"]),key=LEVEL_ORDER.get)
    reasons=access["reasons"]+affordability["reasons"]+channel["reasons"]
    return {"access_barriers":access,"affordability_barriers":affordability,
        "channel_opportunity":channel,"overall_opportunity":{"level":overall,"reasons":reasons},
        "statement":"This plan-drug combination has access and affordability barriers that could contribute to medication adherence challenges and may warrant review."}
