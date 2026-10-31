"""
Theory of change for AI governance, as a Monte Carlo.

A portfolio of candidate AI projects is drawn with a risk tier, a value per
month of deployment, a base incident probability and a harm size if an
incident happens. Governance interventions each cover some tiers, cost review
days, cut the incident probability and add deployment delay. The simulation
asks, for every bundle of interventions, how much harm was prevented and how
much value was given up through delay, and where the second number overtakes
the first.
"""

import os
import itertools
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")

TIERS = ["low", "medium", "high"]

INTERVENTIONS = {
    "ethics review board": dict(tiers=["medium", "high"], review_days=20, incident_cut=0.25, delay_days=30),
    "bias testing gate": dict(tiers=["medium", "high"], review_days=8, incident_cut=0.35, delay_days=10),
    "model documentation": dict(tiers=["low", "medium", "high"], review_days=4, incident_cut=0.10, delay_days=5),
    "incident reporting": dict(tiers=["low", "medium", "high"], review_days=2, incident_cut=0.15, delay_days=0),
    "human in the loop": dict(tiers=["high"], review_days=5, incident_cut=0.45, delay_days=15),
    "third party due diligence": dict(tiers=["medium", "high"], review_days=10, incident_cut=0.20, delay_days=20),
}

REVIEW_DAY_COST = 1200.0


def draw_portfolio(n=200, seed=0):
    rng = np.random.default_rng(seed)
    tier = rng.choice(TIERS, size=n, p=[0.5, 0.35, 0.15])
    value_per_month = np.where(tier == "high", rng.lognormal(11.5, 0.5, n),
                       np.where(tier == "medium", rng.lognormal(10.8, 0.5, n),
                                rng.lognormal(10.0, 0.5, n)))
    base_incident = np.where(tier == "high", rng.uniform(0.15, 0.40, n),
                     np.where(tier == "medium", rng.uniform(0.05, 0.15, n),
                              rng.uniform(0.01, 0.05, n)))
    harm = np.where(tier == "high", rng.lognormal(13.5, 0.7, n),
            np.where(tier == "medium", rng.lognormal(12.0, 0.7, n),
                     rng.lognormal(10.5, 0.7, n)))
    third_party = rng.random(n) < 0.4
    return pd.DataFrame(dict(tier=tier, value_per_month=value_per_month,
                             base_incident=base_incident, harm=harm,
                             third_party=third_party))


def apply_bundle(port, bundle):
    """Return incident probability, delay days and review days per project under a bundle."""
    p = port["base_incident"].values.copy()
    delay = np.zeros(len(port))
    review = np.zeros(len(port))
    for name in bundle:
        iv = INTERVENTIONS[name]
        covered = port["tier"].isin(iv["tiers"]).values
        if name == "third party due diligence":
            covered = covered & port["third_party"].values
        p = np.where(covered, p * (1 - iv["incident_cut"]), p)
        delay = delay + covered * iv["delay_days"]
        review = review + covered * iv["review_days"]
    return p, delay, review


def evaluate(port, bundle, runs=300, seed=1):
    rng = np.random.default_rng(seed)
    p0 = port["base_incident"].values
    p1, delay, review = apply_bundle(port, bundle)
    harm = port["harm"].values
    value_day = port["value_per_month"].values / 30.0
    prevented = []
    for _ in range(runs):
        u = rng.random(len(port))
        incidents_base = u < p0
        incidents_gov = u < p1
        prevented.append(((incidents_base & ~incidents_gov) * harm).sum())
    harm_prevented = float(np.mean(prevented))
    value_forgone = float((delay * value_day).sum())
    review_cost = float((review * REVIEW_DAY_COST).sum())
    return dict(bundle=" + ".join(bundle) if bundle else "none",
                n_interventions=len(bundle),
                harm_prevented=harm_prevented,
                value_forgone=value_forgone,
                review_cost=review_cost,
                net_benefit=harm_prevented - value_forgone - review_cost,
                mean_delay_days=float(delay.mean()),
                incidents_avoided=float(((p0 - p1)).sum()))


def tier_breakdown(port, bundle, seed=1):
    p1, delay, review = apply_bundle(port, bundle)
    df = port.copy()
    df["expected_harm_prevented"] = (df["base_incident"] - p1) * df["harm"]
    df["value_forgone"] = delay * df["value_per_month"] / 30.0
    df["review_cost"] = review * REVIEW_DAY_COST
    g = df.groupby("tier")[["expected_harm_prevented", "value_forgone", "review_cost"]].sum()
    g["net"] = g["expected_harm_prevented"] - g["value_forgone"] - g["review_cost"]
    return g.loc[TIERS]


def all_bundles():
    names = list(INTERVENTIONS)
    out = []
    for k in range(len(names) + 1):
        for combo in itertools.combinations(names, k):
            out.append(list(combo))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    port = draw_portfolio()
    results = pd.DataFrame([evaluate(port, b) for b in all_bundles()])
    results = results.sort_values("net_benefit", ascending=False).reset_index(drop=True)
    results.round(0).to_csv(os.path.join(OUT, "bundle_results.csv"), index=False)

    best = results.iloc[0]
    full = results[results["n_interventions"] == len(INTERVENTIONS)].iloc[0]
    print("portfolio:", len(port), "projects,", dict(port["tier"].value_counts()))
    print("best bundle:", best["bundle"])
    print("  harm prevented %.0f, value forgone %.0f, review cost %.0f, net %.0f" % (
        best["harm_prevented"], best["value_forgone"], best["review_cost"], best["net_benefit"]))
    print("everything on:", full["bundle"])
    print("  harm prevented %.0f, value forgone %.0f, review cost %.0f, net %.0f" % (
        full["harm_prevented"], full["value_forgone"], full["review_cost"], full["net_benefit"]))
    over = results[results["value_forgone"] + results["review_cost"] > results["harm_prevented"]]
    print("bundles where governance cost exceeds prevented harm:", len(over), "of", len(results))

    fig, ax = plt.subplots(figsize=(8, 6))
    cost = (results["value_forgone"] + results["review_cost"]) / 1e6
    ax.scatter(cost, results["harm_prevented"] / 1e6, c=results["n_interventions"], cmap="viridis", s=30)
    lim = max(cost.max(), results["harm_prevented"].max() / 1e6)
    ax.plot([0, lim], [0, lim], linestyle=":", color="grey")
    ax.scatter([cost.iloc[0]], [results["harm_prevented"].iloc[0] / 1e6], marker="*", s=200, color="red", label="best net benefit")
    ax.set_xlabel("governance cost, million dollars (value forgone plus review)")
    ax.set_ylabel("expected harm prevented, million dollars")
    ax.set_title("Every intervention bundle, colour = number of interventions")
    ax.text(0.02, 0.95, "below the line: governance costs more than it prevents", transform=ax.transAxes, fontsize=9)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "frontier.png"), dpi=120)
    plt.close(fig)

    bb = tier_breakdown(port, best["bundle"].split(" + ") if best["bundle"] != "none" else [])
    fb = tier_breakdown(port, list(INTERVENTIONS))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, g, title in [(axes[0], bb, "best bundle"), (axes[1], fb, "everything on")]:
        x = np.arange(len(TIERS))
        ax.bar(x - 0.2, g["expected_harm_prevented"] / 1e6, 0.4, label="harm prevented")
        ax.bar(x + 0.2, (g["value_forgone"] + g["review_cost"]) / 1e6, 0.4, label="governance cost")
        ax.set_xticks(x)
        ax.set_xticklabels(TIERS)
        ax.set_title(title)
        ax.set_xlabel("risk tier")
    axes[0].set_ylabel("million dollars")
    axes[0].legend()
    fig.suptitle("Where governance pays off by risk tier")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "tier_breakdown.png"), dpi=120)
    plt.close(fig)
    bb.round(0).to_csv(os.path.join(OUT, "tier_breakdown_best.csv"))
    fb.round(0).to_csv(os.path.join(OUT, "tier_breakdown_full.csv"))


if __name__ == "__main__":
    main()
