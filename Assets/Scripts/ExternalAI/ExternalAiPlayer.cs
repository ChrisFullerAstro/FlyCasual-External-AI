using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using GameModes;
using Ship;
using SubPhases;
using UnityEngine;

namespace ExternalAI
{
    /// <summary>
    /// AI Player that uses external Python AI agent for decision making.
    /// Falls back to Aggressor AI if external agent is unavailable.
    /// </summary>
    public class ExternalAiPlayer : Players.AggressorAiPlayer
    {
        private ExternalAiClient _aiClient;
        private string _gameId;
        private StrategicPlan _currentPlan;
        private Dictionary<string, string> _plannedManeuvers;
        private bool _useExternalAi = true;
        private bool _externalAiAvailable = false;

        public ExternalAiPlayer() : base()
        {
            Name = "External AI";
            NickName = "Claude";
            Title = "LLM Agent";
            Avatar = "UpgradesList.SecondEdition.IG88D";

            _aiClient = new ExternalAiClient();
            _gameId = Guid.NewGuid().ToString();
            _plannedManeuvers = new Dictionary<string, string>();
        }

        public override void SetupShip()
        {
            // Use default setup for now, could be enhanced with external AI later
            base.SetupShip();
        }

        /// <summary>
        /// Called at the start of planning phase to assign maneuvers to all ships.
        /// </summary>
        public override void AssignManeuversStart()
        {
            Roster.HighlightPlayer(PlayerNo);

            if (_useExternalAi)
            {
                // Start async process to get maneuvers from external AI
                RequestExternalManeuvers();
            }
            else
            {
                base.AssignManeuversStart();
            }
        }

        private async void RequestExternalManeuvers()
        {
            try
            {
                // Check if external AI is available
                _externalAiAvailable = await _aiClient.HealthCheck();

                if (!_externalAiAvailable)
                {
                    Debug.LogWarning("External AI not available, falling back to Aggressor AI");
                    base.AssignManeuversStart();
                    return;
                }

                // Export current game state
                var gameState = GameStateExporter.Export(
                    _gameId,
                    Phases.RoundCounter,
                    "planning",
                    PlayerNo
                );

                // If this is round 1, create strategic plan first
                if (Phases.RoundCounter == 1 && _currentPlan == null)
                {
                    Debug.Log("Requesting strategic plan from external AI...");
                    var planResponse = await _aiClient.RequestStrategicPlan(_gameId, gameState);

                    // Validate response
                    if (planResponse?.plan == null)
                    {
                        Debug.LogError("Strategic plan response was null, falling back to Aggressor AI");
                        base.AssignManeuversStart();
                        return;
                    }

                    _currentPlan = planResponse.plan;
                    Debug.Log($"Strategic plan received: {_currentPlan.win_condition}");
                }

                // Start round session
                Debug.Log($"Starting round {Phases.RoundCounter} session...");
                await _aiClient.StartRound(_gameId, Phases.RoundCounter, gameState);

                // Request planning decisions
                Debug.Log("Requesting maneuver decisions...");
                var decision = await _aiClient.RequestDecision(DecisionType.Planning);

                // Validate decision response
                if (decision == null)
                {
                    Debug.LogError("Decision response was null, falling back to Aggressor AI");
                    base.AssignManeuversStart();
                    return;
                }

                if (!decision.success || decision.planning?.maneuvers == null)
                {
                    Debug.LogError($"External AI decision failed: {decision.error ?? "no maneuvers returned"}");
                    base.AssignManeuversStart();
                    return;
                }

                // Store planned maneuvers
                _plannedManeuvers.Clear();
                Debug.Log($"Received {decision.planning.maneuvers.Count} maneuver decisions from AI");

                foreach (var maneuver in decision.planning.maneuvers)
                {
                    // Validate each maneuver entry
                    if (maneuver == null)
                    {
                        Debug.LogWarning("Null maneuver entry in list, skipping");
                        continue;
                    }

                    if (string.IsNullOrEmpty(maneuver.ship_id))
                    {
                        Debug.LogWarning("Maneuver has null/empty ship_id, skipping");
                        continue;
                    }

                    if (string.IsNullOrEmpty(maneuver.maneuver_code))
                    {
                        Debug.LogWarning($"Maneuver for ship {maneuver.ship_id} has null/empty code, skipping");
                        continue;
                    }

                    string convertedCode = ConvertManeuverCode(maneuver.maneuver_code);
                    Debug.Log($"Ship {maneuver.ship_id}: {maneuver.maneuver_code} -> {convertedCode}");
                    _plannedManeuvers[maneuver.ship_id] = convertedCode;

                    if (!string.IsNullOrEmpty(maneuver.reasoning))
                    {
                        Debug.Log($"Reasoning: {maneuver.reasoning.Substring(0, Math.Min(100, maneuver.reasoning.Length))}");
                    }
                }

                // Now proceed with assigning maneuvers
                AssignExternalManeuversRecursive();
            }
            catch (Exception ex)
            {
                Debug.LogError($"External AI error: {ex.Message}");
                _externalAiAvailable = false;
                base.AssignManeuversStart();
            }
        }

        private void AssignExternalManeuversRecursive()
        {
            var shipWithoutManeuver = GetNextShipWithoutAssignedManeuver();

            if (shipWithoutManeuver != null)
            {
                Selection.ChangeActiveShip(shipWithoutManeuver);

                // Open the dial UI silently
                GameMode.CurrentGameMode.ExecuteCommand(
                    PlanningSubPhase.GenerateSelectShipToAssignManeuver(Selection.ThisShip.ShipId)
                );
            }
            else
            {
                // All ships assigned, proceed
                GameMode.CurrentGameMode.ExecuteCommand(UI.GenerateNextButtonCommand());
            }
        }

        private GenericShip GetNextShipWithoutAssignedManeuver()
        {
            return Roster.GetPlayer(Phases.CurrentSubPhase.RequiredPlayer).Ships.Values
                .Where(n => n.AssignedManeuver == null && !n.State.IsIonized)
                .FirstOrDefault();
        }

        /// <summary>
        /// Called for each ship to assign its maneuver.
        /// </summary>
        public override void AskAssignManeuver()
        {
            if (_useExternalAi && _externalAiAvailable && _plannedManeuvers.Count > 0)
            {
                string shipId = Selection.ThisShip.ShipId.ToString();

                if (_plannedManeuvers.TryGetValue(shipId, out string maneuverCode))
                {
                    // Validate the maneuver exists on this ship's dial
                    if (!Selection.ThisShip.HasManeuver(maneuverCode))
                    {
                        Debug.LogError($"Ship {shipId} ({Selection.ThisShip.PilotInfo.PilotName}) does not have maneuver {maneuverCode}!");
                        Debug.Log($"Available maneuvers: {string.Join(", ", Selection.ThisShip.Maneuvers.Keys)}");

                        // Try to find a similar valid maneuver as fallback
                        string fallbackManeuver = FindFallbackManeuver(Selection.ThisShip, maneuverCode);
                        if (fallbackManeuver != null)
                        {
                            Debug.Log($"Using fallback maneuver: {fallbackManeuver}");
                            maneuverCode = fallbackManeuver;
                        }
                        else
                        {
                            Debug.LogWarning("No fallback found, using Aggressor AI");
                            base.AskAssignManeuver();
                            return;
                        }
                    }

                    Debug.Log($"Assigning external AI maneuver to ship {shipId}: {maneuverCode}");
                    ShipMovementScript.SendAssignManeuverCommand(maneuverCode);

                    // Wait for command to process before continuing (matches NavigationSubSystem behavior)
                    GameManagerScript.Wait(0.2f, delegate {
                        Selection.DeselectThisShip();
                        AssignExternalManeuversRecursive();
                    });
                }
                else
                {
                    // Fallback for ships not in plan
                    Debug.LogWarning($"No planned maneuver for ship {shipId}, using fallback");
                    base.AskAssignManeuver();
                }
            }
            else
            {
                base.AskAssignManeuver();
            }
        }

        /// <summary>
        /// Find a fallback maneuver when the AI picks an invalid one.
        /// Tries to find a similar maneuver at lower speed.
        /// </summary>
        private string FindFallbackManeuver(GenericShip ship, string invalidManeuver)
        {
            var parts = invalidManeuver.Split('.');
            if (parts.Length < 3) return null;

            int speed = int.Parse(parts[0]);
            string direction = parts[1];
            string bearing = parts[2];

            // Try same bearing at lower speeds
            for (int s = speed - 1; s >= 1; s--)
            {
                string candidate = $"{s}.{direction}.{bearing}";
                if (ship.HasManeuver(candidate))
                    return candidate;
            }

            // Try straight at same speed
            string straight = $"{speed}.F.S";
            if (ship.HasManeuver(straight))
                return straight;

            // Try 2 straight as safe default
            if (ship.HasManeuver("2.F.S"))
                return "2.F.S";

            return null;
        }

        /// <summary>
        /// Called during activation phase to perform maneuvers.
        /// Override to avoid using VirtualBoard which wasn't initialized.
        /// </summary>
        public override void PerformManeuver()
        {
            Roster.HighlightPlayer(PlayerNo);

            // Use simple implementation instead of NavigationSubSystem which requires VirtualBoard
            GenericShip nextShip = GetNextShipWithoutFinishedManeuver();

            if (nextShip != null)
            {
                Selection.ChangeActiveShip("ShipId:" + nextShip.ShipId);
                ActivateShip(nextShip);
            }
            else
            {
                Phases.Next();
            }
        }

        /// <summary>
        /// Get next ship that hasn't performed its maneuver yet.
        /// Simple implementation that doesn't require VirtualBoard.
        /// </summary>
        private GenericShip GetNextShipWithoutFinishedManeuver()
        {
            return Roster.GetPlayer(Phases.CurrentSubPhase.RequiredPlayer).Ships.Values
                .Where(n => !n.IsManeuverPerformed)
                .FirstOrDefault();
        }

        /// <summary>
        /// Called to select attack target during engagement phase.
        /// </summary>
        protected override GenericShip SelectTargetForAttack()
        {
            if (!_useExternalAi || !_externalAiAvailable)
            {
                return base.SelectTargetForAttack();
            }

            // For now, use base implementation
            // TODO: Implement async target selection from external AI
            return base.SelectTargetForAttack();
        }

        /// <summary>
        /// Convert from Python format (2_straight) to FlyCasual format (2.F.S)
        /// </summary>
        private string ConvertManeuverCode(string pythonCode)
        {
            // Python format: "2_straight", "2_bank_left", "3_turn_right"
            // FlyCasual format: "2.F.S", "2.L.B", "3.R.T"

            if (string.IsNullOrEmpty(pythonCode))
            {
                Debug.LogError("ConvertManeuverCode received null/empty code");
                return "2.F.S"; // Safe fallback
            }

            var parts = pythonCode.Split('_');
            if (parts.Length < 2)
            {
                Debug.LogWarning($"ConvertManeuverCode: unexpected format '{pythonCode}', expected 'speed_type'");
                return pythonCode;
            }

            string speed = parts[0];
            string maneuverType = string.Join("_", parts.Skip(1));

            string direction = "F";  // Forward
            string bearing;

            switch (maneuverType)
            {
                case "straight":
                    direction = "F";
                    bearing = "S";
                    break;
                case "bank_left":
                    direction = "L";
                    bearing = "B";
                    break;
                case "bank_right":
                    direction = "R";
                    bearing = "B";
                    break;
                case "turn_left":
                    direction = "L";
                    bearing = "T";
                    break;
                case "turn_right":
                    direction = "R";
                    bearing = "T";
                    break;
                case "kturn":
                    direction = "F";
                    bearing = "K";
                    break;
                case "sloop_left":
                    direction = "L";
                    bearing = "E";  // Segnor's Loop
                    break;
                case "sloop_right":
                    direction = "R";
                    bearing = "E";
                    break;
                case "talon_left":
                    direction = "L";
                    bearing = "R";  // Tallon Roll
                    break;
                case "talon_right":
                    direction = "R";
                    bearing = "R";
                    break;
                case "reverse_straight":
                    direction = "F";
                    bearing = "V";  // Reverse
                    break;
                case "reverse_bank_left":
                    direction = "L";
                    bearing = "A";
                    break;
                case "reverse_bank_right":
                    direction = "R";
                    bearing = "A";
                    break;
                case "stationary":
                    direction = "F";
                    bearing = "S";
                    speed = "0";
                    break;
                default:
                    // Unknown maneuver type - log and use safe fallback
                    Debug.LogWarning($"Unknown maneuver type: '{maneuverType}' from code '{pythonCode}'");
                    direction = "F";
                    bearing = "S";
                    break;
            }

            string result = $"{speed}.{direction}.{bearing}";
            return result;
        }

        /// <summary>
        /// Toggle external AI on/off
        /// </summary>
        public void SetUseExternalAi(bool use)
        {
            _useExternalAi = use;
        }
    }
}
