using System.Collections.Generic;

namespace ExternalAI
{
    public class StrategicPlanResponse
    {
        public StrategicPlan plan { get; set; }
    }

    public class StrategicPlan
    {
        public string initial_analysis { get; set; }
        public List<string> my_squad_strengths { get; set; }
        public List<string> my_squad_weaknesses { get; set; }
        public List<string> enemy_threats { get; set; }
        public string win_condition { get; set; }
        public List<string> target_priority { get; set; }
        public string engagement_style { get; set; }
        public Dictionary<string, string> ship_roles { get; set; }
        public List<string> adjustments { get; set; }
        public string opponent_tendencies { get; set; }
        public int created_turn { get; set; }
        public int last_updated_turn { get; set; }
    }

    public class RoundStartResponse
    {
        public string session_id { get; set; }
    }

    public class DecisionResponse
    {
        public string decision_type { get; set; }
        public bool success { get; set; }
        public string error { get; set; }
        public PlanningResponse planning { get; set; }
        public TargetDecision target { get; set; }
        public string thinking_trace { get; set; }
    }

    public class PlanningResponse
    {
        public List<ManeuverDecision> maneuvers { get; set; }
        public string strategic_thinking { get; set; }
    }

    public class ManeuverDecision
    {
        public string ship_id { get; set; }
        public string maneuver_code { get; set; }
        public string reasoning { get; set; }
    }

    public class TargetDecision
    {
        public string attacker_id { get; set; }
        public string target_id { get; set; }
        public string weapon { get; set; }
        public string reasoning { get; set; }
    }

    public class RoundEndResponse
    {
        public RoundSummary summary { get; set; }
        public StrategicPlan updated_plan { get; set; }
    }

    public class RoundSummary
    {
        public int round_number { get; set; }
        public string position_summary { get; set; }
        public List<string> damage_events { get; set; }
        public List<string> ships_destroyed { get; set; }
        public string what_went_well { get; set; }
        public string what_went_poorly { get; set; }
        public string enemy_patterns_observed { get; set; }
        public List<string> next_round_priorities { get; set; }
        public List<string> strategic_adjustments { get; set; }
    }
}
