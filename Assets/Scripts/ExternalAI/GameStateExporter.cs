using System.Collections.Generic;
using System.Linq;
using Ship;
using Obstacles;
using Tokens;

namespace ExternalAI
{
    /// <summary>
    /// Exports FlyCasual game state to JSON-serializable format.
    /// </summary>
    public static class GameStateExporter
    {
        public static GameStateExport Export(string gameId, int turnNumber, string phase, Players.PlayerNo aiPlayerNo)
        {
            var export = new GameStateExport
            {
                game_id = gameId,
                turn_number = turnNumber,
                phase = phase,
                board_width = 914.4f,
                board_height = 914.4f,
                my_ships = new List<ShipExport>(),
                enemy_ships = new List<ShipExport>(),
                obstacles = new List<ObstacleExport>()
            };

            // Export ships
            foreach (var ship in Roster.AllShips.Values)
            {
                var shipExport = ExportShip(ship);

                if (ship.Owner.PlayerNo == aiPlayerNo)
                    export.my_ships.Add(shipExport);
                else
                    export.enemy_ships.Add(shipExport);
            }

            // Export obstacles
            foreach (var obstacle in ObstaclesManager.GetPlacedObstacles())
            {
                export.obstacles.Add(ExportObstacle(obstacle));
            }

            return export;
        }

        private static ShipExport ExportShip(GenericShip ship)
        {
            var position = ship.GetPosition();
            var angles = ship.GetAngles();

            return new ShipExport
            {
                id = ship.ShipId.ToString(),
                name = ship.PilotInfo.PilotName,
                ship_type = ship.ShipInfo.ShipName,
                faction = ship.Faction.ToString().ToLower(),

                position = new PositionExport
                {
                    x = position.x * 10,  // Convert to mm
                    y = position.z * 10,
                    heading = NormalizeHeading(angles.y)
                },

                initiative = ship.PilotInfo.Initiative,
                attack = ship.ShipInfo.Firepower,
                agility = ship.ShipInfo.Agility,
                hull = ship.ShipInfo.Hull,
                shields = ship.ShipInfo.Shields,

                current_hull = ship.State.HullCurrent,
                current_shields = ship.State.ShieldsCurrent,
                stress = ship.Tokens.CountTokensByType(typeof(StressToken)),

                tokens = ExportTokens(ship),
                available_maneuvers = ExportManeuvers(ship),
                upgrades = ship.UpgradeBar.GetUpgradesAll()
                    .Select(u => u.UpgradeInfo.Name).ToList(),

                base_size = ship.ShipInfo.BaseSize.ToString().ToLower(),
                primary_arc = "front"  // Simplified
            };
        }

        private static float NormalizeHeading(float heading)
        {
            // Normalize to 0-360 range
            heading = heading % 360;
            if (heading < 0) heading += 360;
            return heading;
        }

        private static List<string> ExportTokens(GenericShip ship)
        {
            var tokens = new List<string>();

            if (ship.Tokens.HasToken(typeof(FocusToken)))
                tokens.Add("focus");
            if (ship.Tokens.HasToken(typeof(EvadeToken)))
                tokens.Add("evade");
            if (ship.Tokens.HasToken(typeof(CalculateToken)))
                tokens.Add("calculate");

            // Add locks with target
            var blueTargetLocks = ship.Tokens.GetTokens<BlueTargetLockToken>('*');
            foreach (var lockToken in blueTargetLocks)
            {
                var targetShip = Roster.AllShips.Values.FirstOrDefault(s =>
                    s.Tokens.HasToken<RedTargetLockToken>(lockToken.Letter));
                if (targetShip != null)
                {
                    tokens.Add($"lock:{targetShip.ShipId}");
                }
            }

            return tokens;
        }

        private static List<ManeuverExport> ExportManeuvers(GenericShip ship)
        {
            var maneuvers = new List<ManeuverExport>();

            foreach (var kvp in ship.DialInfo.PrintedDial)
            {
                var move = kvp.Key;
                var color = kvp.Value;

                string type = ConvertBearingToType(move.Bearing);
                string difficulty = ConvertColorToDifficulty(color);

                maneuvers.Add(new ManeuverExport
                {
                    speed = move.SpeedIntUnsigned,
                    type = type,
                    difficulty = difficulty
                });
            }

            return maneuvers;
        }

        private static string ConvertBearingToType(Movement.ManeuverBearing bearing)
        {
            switch (bearing)
            {
                case Movement.ManeuverBearing.Straight:
                    return "straight";
                case Movement.ManeuverBearing.Bank:
                    return "bank_right";  // Default, will be determined by direction
                case Movement.ManeuverBearing.Turn:
                    return "turn_right";
                case Movement.ManeuverBearing.KoiogranTurn:
                    return "kturn";
                case Movement.ManeuverBearing.SegnorsLoop:
                    return "sloop_right";
                case Movement.ManeuverBearing.TallonRoll:
                    return "talon_right";
                case Movement.ManeuverBearing.Stationary:
                    return "stationary";
                case Movement.ManeuverBearing.ReverseStraight:
                    return "reverse_straight";
                case Movement.ManeuverBearing.ReverseBank:
                    return "reverse_bank_right";
                default:
                    return "straight";
            }
        }

        private static string ConvertColorToDifficulty(Movement.MovementComplexity color)
        {
            switch (color)
            {
                case Movement.MovementComplexity.Easy:
                    return "blue";
                case Movement.MovementComplexity.Normal:
                    return "white";
                case Movement.MovementComplexity.Complex:
                    return "red";
                default:
                    return "white";
            }
        }

        private static ObstacleExport ExportObstacle(GenericObstacle obstacle)
        {
            var position = obstacle.ObstacleGO.transform.position;

            string obstacleType = "asteroid";
            if (obstacle.GetType().Name.ToLower().Contains("debris"))
                obstacleType = "debris";
            else if (obstacle.GetType().Name.ToLower().Contains("gas"))
                obstacleType = "gas_cloud";

            return new ObstacleExport
            {
                id = obstacle.Name,
                type = obstacleType,
                position = new PositionExport
                {
                    x = position.x * 10,
                    y = position.z * 10,
                    heading = 0
                },
                radius = 40  // Approximate
            };
        }
    }
}
