# AI Governance Theory of Change Simulator

A Monte Carlo that makes a theory of change for AI governance testable. It draws a portfolio of candidate AI projects with risk tiers, deployment value, incident probabilities and harm sizes, then applies every combination of six governance interventions and measures two things for each: the expected harm prevented and the value forgone through review time and deployment delay. The output is a frontier that shows which bundles pay for themselves and which cost more than the harm they prevent.

## Connection to the research

The intervention set and the tiering come from the Theory of Change governance framework developed in MMAI 803 AI Ethics and Policy at Smith School of Business. The question the simulation asks comes from "The Governance Lag: Why Slow AI Adoption Is the Larger Risk" (Rehman, 2026). That paper argues that governance which slows adoption indiscriminately can cost more than the harms it prevents, and that proportionate, risk tiered governance is the way out. A claim like that should be testable, so this repo sets up the accounting: harm prevented on one side, value forgone and review cost on the other, broken down by risk tier. The distributional side of the same argument is in "Who Bears the Cost of Waiting: The Uneven Price of Slow AI Adoption" (Rehman, 2026).

## Why it matters for AI governance in financial services

Every time a governance team proposes a new control it has to make the case internally that the control is worth the friction. This simulation is the shape of that argument. It also shows the tier logic concretely: with the default parameters, controls that cover only high risk projects (human in the loop, incident reporting) have the best net benefit, while applying every control to every project has a negative net benefit because low and medium risk projects pay the delay without much harm to prevent. That is the proportionality principle in the EU AI Act, in Canada's AIDA proposal and in model risk guidance, shown in numbers.

## How it works

`draw_portfolio` creates two hundred synthetic projects with a fixed seed. Half are low risk, a third medium, the rest high. Each has a monthly deployment value, a base incident probability and a harm size if an incident occurs, all drawn from lognormal or uniform distributions that scale with tier. Forty percent involve a third party model.

Six interventions are defined in `INTERVENTIONS` with the tiers they cover, review days, the proportional cut in incident probability and the deployment delay in days. `apply_bundle` applies a set of them to the portfolio. `evaluate` runs the incident draws three hundred times with common random numbers, so harm prevented is the harm from incidents that would have happened without the bundle but not with it. Value forgone is delay days times daily deployment value, review cost is review days times a daily cost. `tier_breakdown` splits the same accounting by risk tier.

`main` evaluates all sixty four bundles, ranks them by net benefit, and plots them.

## Run

```
pip install -r requirements.txt
python simulate.py
pytest
```

Outputs in `outputs/`: `frontier.png` plots every bundle with governance cost on the horizontal axis and harm prevented on the vertical, bundles below the diagonal cost more than they prevent, the best bundle is starred. `tier_breakdown.png` compares harm prevented and governance cost by tier for the best bundle and for everything on. `bundle_results.csv` lists every bundle with its numbers.

In the default run the best bundle is incident reporting plus human in the loop, with roughly 7.4 million in harm prevented against 2.8 million in cost. Turning everything on prevents about 12.1 million in harm but costs about 22.8 million. Forty four of the sixty four bundles cost more than they prevent. The tier chart shows the cost of over governance is almost entirely in the low and medium tiers.

## Parameters to argue with

All of the numbers that drive the result are at the top of `simulate.py`: the intervention table, the review day cost and the distributions in `draw_portfolio`. A reader who thinks the incident cuts are too optimistic, or that harms are larger, can change them and rerun. The structure is the contribution, not the specific values.

## Limitations

The portfolio is synthetic. Interventions are assumed to act independently and multiplicatively on the incident probability, which ignores overlap. Harm is a single dollar figure, so reputational, regulatory and customer harm are collapsed together. Delay cost is linear in days. There is no learning over time and no feedback from incidents to future governance. Real incident rates for AI systems are poorly measured, which is itself a governance problem the incident reporting intervention is meant to fix.

## Author

Saif Rehman, MMAI, Smith School of Business, Queen's University.
