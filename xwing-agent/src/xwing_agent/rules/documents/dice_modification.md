# Dice Modification Rules

## Modification Timing
Dice modification happens in multiple windows during each roll:

**Attack Dice:**
1. Attacker rolls attack dice
2. Attacker modifies (AfterRolled - triggered abilities)
3. Defender modifies (Opposite timing - spend tokens to affect attack dice)
4. Attacker modifies (Normal timing - spend tokens like focus/lock)

**Defense Dice:**
5. Defender rolls defense dice
6. Defender modifies (AfterRolled - triggered abilities)
7. Attacker modifies (Opposite timing - spend tokens to affect defense dice)
8. Defender modifies (Normal timing - spend tokens like focus/evade)

## Modification Order
Within each modification window:
1. Spend tokens/abilities to reroll dice
2. Spend tokens/abilities to change dice results

You cannot reroll a die that has already been rerolled.

## Common Modifications

### Focus Token
- **Cost**: Spend 1 focus token
- **Effect**: Change ALL focus results to hits (attack) or evades (defense)
- **When**: Modify step

### Target Lock (Reroll)
- **Cost**: Spend the lock on the defender
- **Effect**: Reroll any number of attack dice
- **When**: Modify step (before changing results)
- **Note**: Lock is removed after spending

### Calculate Token
- **Cost**: Spend 1 calculate token
- **Effect**: Change 1 focus result to a hit or evade
- **When**: Modify step
- **Note**: Can spend multiple calculates for multiple focus results

### Evade Token
- **Cost**: Spend 1 evade token
- **Effect**: Add 1 evade result to defense roll
- **When**: Modify step

### Force Charge
- **Cost**: Spend 1 force charge
- **Effect**: Change 1 focus result to a hit or evade
- **When**: Modify step
- **Note**: Force charges regenerate during End Phase

## Optimal Modification Strategy

### Attacking
1. Reroll blanks and focuses (if no focus token)
2. Then spend focus token to convert remaining focuses
3. Lock + Focus is strongest combo: reroll bad dice, then convert focuses

### Defending
1. Spend focus token if you have focus results
2. Add evade token results
3. Use force/calculate for any remaining focus results

## Special Abilities
Many pilot abilities and upgrades modify dice:
- "Before rolling, you may change 1 die to [result]"
- "After rolling, you may reroll up to 2 dice"
- "Add 1 [result] result"

These have specific timing - read carefully whether they happen before, during, or after the modify step.
