using System.Collections.Generic;

namespace ExternalAI
{
    public class GameStateExport
    {
        public string game_id { get; set; }
        public int turn_number { get; set; }
        public string phase { get; set; }
        public float board_width { get; set; }
        public float board_height { get; set; }
        public List<ShipExport> my_ships { get; set; }
        public List<ShipExport> enemy_ships { get; set; }
        public List<ObstacleExport> obstacles { get; set; }
        public int my_points_destroyed { get; set; }
        public int enemy_points_destroyed { get; set; }
    }

    public class PositionExport
    {
        public float x { get; set; }
        public float y { get; set; }
        public float heading { get; set; }
    }

    public class ShipExport
    {
        public string id { get; set; }
        public string name { get; set; }
        public string ship_type { get; set; }
        public string faction { get; set; }

        public PositionExport position { get; set; }

        public int initiative { get; set; }
        public int attack { get; set; }
        public int agility { get; set; }
        public int hull { get; set; }
        public int shields { get; set; }

        public int current_hull { get; set; }
        public int current_shields { get; set; }
        public int stress { get; set; }

        public List<string> tokens { get; set; }
        public List<ManeuverExport> available_maneuvers { get; set; }
        public List<string> upgrades { get; set; }

        public string base_size { get; set; }
        public string primary_arc { get; set; }
    }

    public class ManeuverExport
    {
        public int speed { get; set; }
        public string type { get; set; }
        public string difficulty { get; set; }
    }

    public class ObstacleExport
    {
        public string id { get; set; }
        public string type { get; set; }
        public PositionExport position { get; set; }
        public float radius { get; set; }
    }
}
