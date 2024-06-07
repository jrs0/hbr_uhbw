# This script is a scratchpad for various simple outcome models
#
# In the models below, it is assumed that the outcomes are deterministic
# in the group A, and the job of the prediction tool is to predict these
# outcomes so as to establish the group who will bleed, and apply an
# intervention to them.

# These are the inputs that the app will use
p_b_ni_nb = 0.922
p_b_ni_b = 0.01
p_b_i_nb = 0.066
p_b_i_b = 1 - p_b_ni_nb - p_b_ni_b - p_b_i_nb

# Model 0: Exact prediction of bleeding/ischaemia, intervention
# completely removes bleeding event (no effect on ischaemia)
#
# In this model, it is assumed that bleeding and ischaemia outcomes
# can be predicted exactly, and the intervention (modification of DAPT)
# is such that a bleeding outcome can be entirely (deterministically) removed
# without affecting the ischaemia outcome. No calculation is required to
# establish the outcomes under this model, because all * + B outcomes
# would be added to * + NB categories, resulting in:
#
p_a_ni_nb = p_b_ni_nb + p_b_ni_b
p_a_i_nb = p_b_i_nb + p_b_i_b
p_a_ni_b = 0
p_a_i_b = 0

# Model 1: Exact prediction of bleeding/ischaemia, intervention has
# probability p to remove bleeding event (no effect on ischaemia)
#
# In this model, it is assumed that a patient who will bleed is
# identified deterministically, but the intervention will only
# remove the bleeding event with probability p. However, the
# ischaemia event will not be modified.
#
p = 0.2
p_a_ni_nb = p_b_ni_nb + p * p_b_ni_b
p_a_i_nb = p_b_i_nb + p * p_b_i_b
p_a_ni_b = (1 - p) * p_b_ni_b
p_a_i_b = (1 - p) * p_b_i_b

# Model 2: Exact prediction of bleeding/ischaemia, intervention has
# probability p to remove bleeding event, and probability p to add
# ischaemia event
#
# In this model, bleeding events will be removed with some
# probability, but there is the same probability that an
# ischaemia event is introduced. Since the prediction of original
# outcome is exact (and therefore the intervention is highly
# tailored), there is no effect on outcomes in the group who would
# not bleed (98%)
#
# Here, the decrease in bleeding outweighs the increase in ischaemia
# in whatever proportional split there is between ischaemia and
# non ischaemia in the bleeding group. For example, for a split of
# 50%, bleeding reduced by twice as much as ischaemia increases
# (because all the bleeding events are subject to p, but only half
# of the ischaemia events are, the other half already having an
# ischaemia event.
#
p = 0.2

# Bleeding removed and no ischaemia added
p_a_ni_nb = p_b_ni_nb + p * (1 - p) * p_b_ni_b

# Bleeding removed, and either ischaemia added or already present
p_a_i_nb = p_b_i_nb + p * p_b_i_b + p * p * p_b_ni_b

# Bleeding and ischaemia both unaffected
p_a_ni_b = (1 - p) * (1 - p) * p_b_ni_b

# Bleeding unaffected but ischaemia introduced
p_a_i_b = (1 - p) * p_b_i_b + (1 - p) * p * p_b_ni_b

# Model 3: Inexact prediction of bleeding with probability q,
# intervention completely removes a bleeding event
# and has no effect on ischaemia outcomes
#
# In this model, all the bleeding events correctly predicted will
# be eliminated, and there is no possible adverse effect on ischaemia.
# Therefore, the proportion q of bleeding events will be eliminated,
# that is.
#
q = 0.8
p_a_ni_nb = p_b_ni_nb + q * p_b_ni_b
p_a_i_nb = p_b_i_nb + q * p_b_i_b
p_a_ni_b = (1 - q) * p_b_ni_b
p_a_i_b = (1 - q) * p_b_i_b

# Model 4: Inexact prediction of bleeding with probability q,
# intervention has probability p to remove bleeding event, and
# probability p to add ischaemia event
#
# Note that this model, like all the models above, applies the
# intervention only based on the prediction of bleeding (whether
# or not the patient is predicted to have further ischaemia is
# ignored).
#
# Here, by getting the prediction of bleeding wrong a proportion of
# the time, approximately that same proportion of patients will
# incorrectly receive an intervention that increases the ischaemia
# risk. Since the pool of bleeding patients is so small, it doesn't
# take much for the total ischaemia increase to outweigh the bleeding
# decrease.
#
# This model motivates consideration of an intervention that depends
# on both the ischaemia and risk prediction:
#
# - If predicted NI/B, apply main intervention X
# - If predicted I/B, apply intervention Y designed not to increase
#   ischaemia risk.
#
q = 0.7
p = 0.2

# - Previous NI/NB, (right) no intervention
# - Previous NI/NB, (wrong) intervention, no change in outcomes
# - Previous NI/B, (right) intervention, remove bleeding and no ischaemia change
p_a_ni_nb = q * p_b_ni_nb + (1 - q) * (1 - p) * p_b_ni_nb + q * p * (1 - p) * p_b_ni_b

# - Previous I/NB, (right) no intervention
# - Previous I/NB, (wrong) intervention, no change in outcomes
# - Previous I/B, (right) intervention, remove bleeding
# - Previous NI/NB, (wrong) intervention adds ischaemia
# - Previous NI/B, (right) intervention, remove bleeding but adds ischaemia
p_a_i_nb = (
    q * p_b_i_nb
    + (1 - q) * p_b_i_nb
    + (1 - q) * p * p_b_ni_nb
    + q * p * p * p_b_ni_b
    + q * p * p_b_i_b
)

# - Previous NI/B, (right) intervention, no change in bleeding/ischaemia
# - Previous NI/B, (wrong) no intervention
p_a_ni_b = q * (1 - p) * (1 - p) * p_b_ni_b + (1 - q) * p_b_ni_b

# - Previous I/B, (right) intervention, no change in bleeding
# - Previous I/B, (wrong) no intervention
# - Previous NI/B, (right) intervention, no change in bleeding but adds ischaemia
p_a_i_b = q * (1 - p) * p_b_i_b + (1 - q) * p_b_i_b + q * (1 - p) * p * p_b_ni_b