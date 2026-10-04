"""
Cheer Stunt Pod Optimizer Engine
Generates cheer stunt groups based on:
- Group size: 2 to 5 athletes (ideally 4)
- Base height similarity (|Main Base - Side Base| minimized)
- Backspot height relative to bases (Backspot taller than bases)
- Skill strategy: Balanced vs. Stacked (Tiers)
- Role constraints and secondary flexibility
"""
import copy
import random
from typing import List, Dict, Any, Optional, Tuple

def can_fill_role(athlete: Dict[str, Any], target_role: str) -> bool:
    """Checks if an athlete can fill a target role based on primary and secondary roles."""
    if not athlete:
        return False
    primary = athlete.get("primary_role", "").strip().lower()
    target = target_role.strip().lower()
    
    if primary == target:
        return True
    
    # Generic base handling
    if "base" in target and "base" in primary:
        return True
        
    secondary = athlete.get("secondary_roles") or ""
    if isinstance(secondary, str):
        sec_list = [s.strip().lower() for s in secondary.split(",") if s.strip()]
    elif isinstance(secondary, list):
        sec_list = [str(s).strip().lower() for s in secondary]
    else:
        sec_list = []
        
    for s in sec_list:
        if s == target:
            return True
        if "base" in target and "base" in s:
            return True
            
    return False

def determine_pod_sizes(n_athletes: int, n_flyers: int, strategy: str = "auto") -> List[int]:
    """
    Determines pod sizes for n athletes given the number of available flyers.
    Cheer stunt rule: each stunt pod requires 1 flyer. Pod sizes range from 2 to 5 (ideal: 4).
    """
    if n_athletes < 2 or n_flyers < 1:
        return []
        
    # Cap maximum pods by available flyers
    max_pods = min(n_flyers, n_athletes // 2)
    if max_pods == 0:
        return []

    if strategy == "strict4":
        count = min(max_pods, n_athletes // 4)
        return [4] * count
        
    if strategy == "strict5":
        count = min(max_pods, n_athletes // 5)
        return [5] * count
        
    if strategy == "triads":
        count = min(max_pods, n_athletes // 3)
        return [3] * count
        
    if strategy == "partner":
        count = min(max_pods, n_athletes // 2)
        return [2] * count
        
    # 'auto' strategy:
    # We want pods of size 4 or 5 (ideal 4).
    # If we have n_athletes and max_pods:
    # First, how many pods should we form?
    # If n_athletes / max_pods >= 4:
    # We can form max_pods. For example:
    # 20 athletes, 4 flyers -> 4 pods of 5.
    # 18 athletes, 4 flyers -> two 5s and two 4s.
    # 16 athletes, 4 flyers -> four 4s.
    # 15 athletes, 4 flyers -> three 4s and one 3.
    # 12 athletes, 4 flyers -> four 3s or three 4s.
    
    # Target number of pods:
    pods_count = min(max_pods, (n_athletes + 3) // 4)
    # Ensure average size is between 2 and 5
    while pods_count > 1 and (n_athletes / pods_count) < 2.5:
        pods_count -= 1
        
    while pods_count < max_pods and (n_athletes / pods_count) > 5.0:
        pods_count += 1
        
    # Now distribute n_athletes into pods_count bins, each size between 2 and 5
    # Base size:
    base_size = min(4, n_athletes // pods_count)
    if base_size < 2:
        base_size = 2
    sizes = [base_size] * pods_count
    
    current_total = sum(sizes)
    # Distribute extra athletes up to max 5 per pod
    idx = 0
    while current_total < n_athletes and idx < pods_count:
        if sizes[idx] < 5:
            sizes[idx] += 1
            current_total += 1
        idx = (idx + 1) % pods_count
        if all(s >= 5 for s in sizes):
            break
            
    return sizes

def evaluate_pod(pod: Dict[str, Any], mode: str = "balanced", target_skill: float = 3.0) -> Tuple[float, Dict[str, Any]]:
    """
    Calculates cost / penalty for a pod. Lower is better.
    Also returns rich metrics for coach display.
    """
    penalty = 0.0
    main_b = pod.get("main_base")
    side_b = pod.get("side_base")
    back_s = pod.get("backspot")
    flyer = pod.get("flyer")
    front_s = pod.get("front_spot")
    
    metrics = {
        "base_diff": None,
        "base_rating": "N/A",
        "backspot_clearance": None,
        "backspot_rating": "N/A",
        "avg_skill": 0.0,
        "total_skill": 0,
        "warnings": [],
        "strengths": []
    }
    
    # 1. Base Height Delta
    if main_b and side_b:
        diff = abs(main_b["height_inches"] - side_b["height_inches"])
        metrics["base_diff"] = round(diff, 1)
        if diff <= 0.5:
            metrics["base_rating"] = "Perfect Match"
            metrics["strengths"].append(f"Level base height ({diff:.1f}\" diff)")
            penalty += diff * 1.0
        elif diff <= 1.2:
            metrics["base_rating"] = "Good Match"
            metrics["strengths"].append(f"Solid base height ({diff:.1f}\" diff)")
            penalty += 1.0 + (diff - 0.5) * 6.0
        elif diff <= 2.0:
            metrics["base_rating"] = "Acceptable"
            metrics["warnings"].append(f"Noticeable base height diff ({diff:.1f}\")")
            penalty += 8.0 + (diff - 1.2) * 15.0
        else:
            metrics["base_rating"] = "High Delta"
            metrics["warnings"].append(f"Significant base height mismatch ({diff:.1f}\")")
            penalty += 25.0 + (diff - 2.0) * 30.0
            
        max_base_h = max(main_b["height_inches"], side_b["height_inches"])
        avg_base_h = (main_b["height_inches"] + side_b["height_inches"]) / 2.0
    elif main_b:
        max_base_h = main_b["height_inches"]
        avg_base_h = main_b["height_inches"]
        metrics["base_rating"] = "Single Base"
    elif side_b:
        max_base_h = side_b["height_inches"]
        avg_base_h = side_b["height_inches"]
        metrics["base_rating"] = "Single Base"
    else:
        max_base_h = 0
        avg_base_h = 0

    # 2. Backspot Height vs Bases (Backspot MUST be taller than bases)
    if back_s and max_base_h > 0:
        clearance = back_s["height_inches"] - max_base_h
        metrics["backspot_clearance"] = round(clearance, 1)
        if clearance >= 1.5:
            metrics["backspot_rating"] = "Optimal Reach"
            metrics["strengths"].append(f"Backspot +{clearance:.1f}\" taller than bases")
            penalty += 0.0
        elif clearance >= 0.0:
            metrics["backspot_rating"] = "Level Reach"
            penalty += 3.0 + (1.5 - clearance) * 4.0
        elif clearance >= -1.0:
            metrics["backspot_rating"] = "Slightly Short"
            metrics["warnings"].append(f"Backspot is {abs(clearance):.1f}\" shorter than tallest base")
            penalty += 30.0 + abs(clearance) * 20.0
        else:
            metrics["backspot_rating"] = "Too Short"
            metrics["warnings"].append(f"Backspot is {abs(clearance):.1f}\" shorter than bases (safety risk)")
            penalty += 70.0 + abs(clearance) * 40.0
    elif back_s:
        metrics["backspot_rating"] = "No Bases to Compare"

    # 3. Flyer relative height check
    if flyer and avg_base_h > 0:
        if flyer["height_inches"] > avg_base_h + 1.0:
            metrics["warnings"].append(f"Flyer is taller than base average")
            penalty += 20.0

    # 4. Skill calculations
    active_members = [a for a in [flyer, main_b, side_b, back_s, front_s] if a]
    if active_members:
        tot_skill = sum(a["skill_level"] for a in active_members)
        avg_skill = tot_skill / len(active_members)
        metrics["total_skill"] = tot_skill
        metrics["avg_skill"] = round(avg_skill, 1)
        
        if mode == "balanced":
            # Penalize deviation from squad mean
            penalty += abs(avg_skill - target_skill) * 15.0
            # Encourage at least one experienced anchor (skill >= 4)
            has_anchor = any(a["skill_level"] >= 4 for a in active_members)
            if not has_anchor:
                penalty += 12.0
                metrics["warnings"].append("No senior stunt anchor (skill 4+) in this pod")

    return penalty, metrics

def optimize_stunt_groups(
    athletes: List[Dict[str, Any]],
    mode: str = "balanced",
    size_strategy: str = "auto"
) -> Dict[str, Any]:
    """
    Main algorithm that takes active/checked athletes and constructs the optimal stunt pods.
    """
    # Filter active athletes
    active = [a for a in athletes if a.get("is_checked", True) and a.get("is_active", 1) == 1]
    n = len(active)
    
    if n < 2:
        return {
            "pods": [],
            "unassigned": active,
            "mode": mode,
            "total_active": n,
            "message": "Please select at least 2 present athletes to form a stunt group."
        }
        
    squad_avg_skill = sum(a["skill_level"] for a in active) / n
    n_flyers = sum(1 for a in active if can_fill_role(a, "flyer"))
    target_sizes = determine_pod_sizes(n, n_flyers=n_flyers, strategy=size_strategy)
    
    if not target_sizes:
        return {
            "pods": [],
            "unassigned": active,
            "mode": mode,
            "total_active": n,
            "message": "Cannot form any pods with the selected criteria."
        }

    # Best state tracking
    best_pods = []
    best_cost = float("inf")
    
    # We run stochastic multi-start search with greedy initialization
    num_runs = 350 if n <= 24 else 150
    
    for _ in range(num_runs):
        pool = list(active)
        random.shuffle(pool)
        
        # Sort candidates according to mode
        flyers_pool = [a for a in pool if can_fill_role(a, "flyer")]
        bases_pool = [a for a in pool if can_fill_role(a, "main base") or can_fill_role(a, "side base")]
        backs_pool = [a for a in pool if can_fill_role(a, "backspot")]
        fronts_pool = [a for a in pool if can_fill_role(a, "front spot")]
        
        if mode == "stacked":
            flyers_pool.sort(key=lambda x: x["skill_level"], reverse=True)
            bases_pool.sort(key=lambda x: x["skill_level"], reverse=True)
            backs_pool.sort(key=lambda x: x["skill_level"], reverse=True)
        else:
            # Balanced: slight shuffle with primary role priority
            flyers_pool.sort(key=lambda x: (x.get("primary_role", "").lower() == "flyer", random.random()), reverse=True)
            
        used_ids = set()
        constructed_pods = []
        
        for p_idx, target_size in enumerate(target_sizes):
            pod = {
                "id": p_idx + 1,
                "target_size": target_size,
                "flyer": None,
                "main_base": None,
                "side_base": None,
                "backspot": None,
                "front_spot": None
            }
            
            # Step 1: Flyer
            avail_flyers = [a for a in flyers_pool if a["id"] not in used_ids]
            if avail_flyers:
                # Prefer primary flyer first
                prim = [a for a in avail_flyers if a.get("primary_role", "").lower() == "flyer"]
                chosen_flyer = prim[0] if prim else avail_flyers[0]
                pod["flyer"] = chosen_flyer
                used_ids.add(chosen_flyer["id"])
                
            # Step 2: Bases
            avail_bases = [a for a in bases_pool if a["id"] not in used_ids]
            if target_size >= 4:
                # Needs 2 bases: Main Base & Side Base
                if len(avail_bases) >= 2:
                    # Pick best height match pair among available bases
                    best_pair = None
                    min_diff = 999.0
                    sample_limit = min(8, len(avail_bases))
                    for i in range(sample_limit):
                        for j in range(i + 1, sample_limit):
                            b1, b2 = avail_bases[i], avail_bases[j]
                            d = abs(b1["height_inches"] - b2["height_inches"])
                            if d < min_diff:
                                min_diff = d
                                best_pair = (b1, b2)
                                if d <= 0.4:
                                    break
                        if best_pair and min_diff <= 0.4:
                            break
                            
                    if not best_pair:
                        best_pair = (avail_bases[0], avail_bases[1])
                        
                    b1, b2 = best_pair
                    # Assign Main vs Side
                    if b1.get("primary_role", "").lower() == "main base" or b1["skill_level"] >= b2["skill_level"]:
                        pod["main_base"] = b1
                        pod["side_base"] = b2
                    else:
                        pod["main_base"] = b2
                        pod["side_base"] = b1
                    used_ids.add(b1["id"])
                    used_ids.add(b2["id"])
                elif len(avail_bases) == 1:
                    pod["main_base"] = avail_bases[0]
                    used_ids.add(avail_bases[0]["id"])
            elif target_size >= 2:
                # 2 or 3 person pod: at least 1 base
                if avail_bases:
                    pod["main_base"] = avail_bases[0]
                    used_ids.add(avail_bases[0]["id"])
                    if target_size == 3 and len(avail_bases) >= 2 and not pod.get("backspot"):
                        # could be 2 bases or 1 base + backspot
                        pass

            # Step 3: Backspot
            # Target height: Backspot should be taller than max base height in this pod
            max_b_h = 0
            if pod["main_base"]:
                max_b_h = max(max_b_h, pod["main_base"]["height_inches"])
            if pod["side_base"]:
                max_b_h = max(max_b_h, pod["side_base"]["height_inches"])
                
            avail_backs = [a for a in backs_pool if a["id"] not in used_ids]
            if target_size >= 3 and avail_backs:
                # Find backspots taller than max base height
                taller = [a for a in avail_backs if a["height_inches"] >= max_b_h]
                if taller:
                    # Ideal is +1.5 to +3.0 inches taller
                    chosen_back = min(taller, key=lambda a: abs((a["height_inches"] - max_b_h) - 2.0))
                else:
                    # Otherwise tallest available backspot
                    chosen_back = max(avail_backs, key=lambda a: a["height_inches"])
                    
                pod["backspot"] = chosen_back
                used_ids.add(chosen_back["id"])

            # Step 4: Front Spot (for 5-person pod)
            if target_size >= 5:
                avail_fronts = [a for a in fronts_pool if a["id"] not in used_ids]
                if not avail_fronts:
                    # fallback to any available base or athlete
                    avail_fronts = [a for a in pool if a["id"] not in used_ids]
                if avail_fronts:
                    chosen_front = avail_fronts[0]
                    pod["front_spot"] = chosen_front
                    used_ids.add(chosen_front["id"])
                    
            constructed_pods.append(pod)

        # Global Cost Evaluation for this layout
        total_cost = 0.0
        pod_skills = []
        for pod in constructed_pods:
            cost, _ = evaluate_pod(pod, mode=mode, target_skill=squad_avg_skill)
            total_cost += cost
            
            # Record average skill
            mems = [a for a in [pod["flyer"], pod["main_base"], pod["side_base"], pod["backspot"], pod["front_spot"]] if a]
            if mems:
                pod_skills.append(sum(a["skill_level"] for a in mems) / len(mems))
            else:
                pod_skills.append(0.0)

        # Mode-specific global cost penalty
        if mode == "stacked":
            # For stacked, pods should be sorted descending by skill.
            # Penalize any inversions where Pod i has lower skill than Pod i+1
            for i in range(len(pod_skills) - 1):
                if pod_skills[i] < pod_skills[i + 1]:
                    total_cost += (pod_skills[i + 1] - pod_skills[i]) * 35.0
        else:
            # For balanced, penalize high variance among pod average skills
            if len(pod_skills) > 1:
                variance = sum((s - squad_avg_skill) ** 2 for s in pod_skills) / len(pod_skills)
                total_cost += variance * 25.0

        # Penalize incomplete pods
        for pod in constructed_pods:
            mems = [a for a in [pod["flyer"], pod["main_base"], pod["side_base"], pod["backspot"], pod["front_spot"]] if a]
            if len(mems) < pod["target_size"]:
                total_cost += (pod["target_size"] - len(mems)) * 50.0

        if total_cost < best_cost:
            best_cost = total_cost
            best_pods = constructed_pods

    # Finalize and annotate best pods
    final_pods = best_pods or []
    
    # Sort pods if stacked
    def pod_avg_calc(p):
        mems = [a for a in [p.get("flyer"), p.get("main_base"), p.get("side_base"), p.get("backspot"), p.get("front_spot")] if a]
        return (sum(a["skill_level"] for a in mems) / len(mems)) if mems else 0.0

    if mode == "stacked":
        final_pods.sort(key=pod_avg_calc, reverse=True)
        for idx, p in enumerate(final_pods):
            p["id"] = idx + 1
            if idx == 0:
                p["tier_name"] = "Tier 1: Elite Routine"
                p["tier_badge"] = "elite"
            elif idx == 1:
                p["tier_name"] = "Tier 2: Advanced Stunts"
                p["tier_badge"] = "advanced"
            elif idx == 2:
                p["tier_name"] = "Tier 3: Solid Standard"
                p["tier_badge"] = "solid"
            else:
                p["tier_name"] = f"Tier {idx+1}: Developmental"
                p["tier_badge"] = "development"
    else:
        for idx, p in enumerate(final_pods):
            p["id"] = idx + 1
            p["tier_name"] = f"Balanced Pod {idx+1}"
            p["tier_badge"] = "balanced"

    # Annotate metrics
    assigned_ids = set()
    for p in final_pods:
        _, metrics = evaluate_pod(p, mode=mode, target_skill=squad_avg_skill)
        p["metrics"] = metrics
        members = [a for a in [p.get("flyer"), p.get("main_base"), p.get("side_base"), p.get("backspot"), p.get("front_spot")] if a]
        p["athletes"] = members
        p["member_count"] = len(members)
        
        # Stunt pod type
        if p["member_count"] == 5:
            p["stunt_type"] = "Full Pod + Front Spot (5)"
        elif p["member_count"] == 4:
            p["stunt_type"] = "Standard Full Pod (4)"
        elif p["member_count"] == 3:
            p["stunt_type"] = "Modified Pod / Triad (3)"
        elif p["member_count"] == 2:
            p["stunt_type"] = "Partner Stunt (2)"
        else:
            p["stunt_type"] = f"Group of {p['member_count']}"

        for m in members:
            assigned_ids.add(m["id"])

    # Unassigned athletes
    unassigned = [a for a in active if a["id"] not in assigned_ids]
    
    # Recommendation message if there are unassigned athletes
    coach_advice = []
    if unassigned:
        unassigned_roles = [a.get("primary_role", "Athlete") for a in unassigned]
        coach_advice.append(f"{len(unassigned)} athlete(s) currently unassigned on bench: {', '.join(unassigned_roles)}.")
        flyer_un = sum(1 for a in unassigned if can_fill_role(a, "flyer"))
        base_un = sum(1 for a in unassigned if can_fill_role(a, "base"))
        back_un = sum(1 for a in unassigned if can_fill_role(a, "backspot"))
        if flyer_un > 0 and base_un < 2:
            coach_advice.append(f"Tip: Need {max(0, 2 - base_un)} more Base(s) and {max(0, 1 - back_un)} Backspot to form another pod.")

    return {
        "pods": final_pods,
        "unassigned": unassigned,
        "mode": mode,
        "total_active": n,
        "total_pods": len(final_pods),
        "coach_advice": coach_advice,
        "squad_avg_skill": round(squad_avg_skill, 1)
    }
