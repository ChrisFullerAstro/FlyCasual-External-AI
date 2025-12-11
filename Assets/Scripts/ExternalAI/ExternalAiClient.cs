using System;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;
using UnityEngine;

namespace ExternalAI
{
    /// <summary>
    /// HTTP client for communicating with the Python AI agent.
    /// </summary>
    public class ExternalAiClient
    {
        private static readonly HttpClient _client = new HttpClient();
        private const int DEFAULT_PORT = 33293;
        private string _baseUrl = $"http://localhost:{DEFAULT_PORT}/api/v1";
        private string _currentSessionId;

        public ExternalAiClient(string baseUrl = null)
        {
            if (!string.IsNullOrEmpty(baseUrl))
                _baseUrl = baseUrl;

            _client.Timeout = TimeSpan.FromSeconds(60);
        }

        public string CurrentSessionId => _currentSessionId;

        public async Task<StrategicPlanResponse> RequestStrategicPlan(
            string gameId,
            GameStateExport gameState)
        {
            var request = new
            {
                game_id = gameId,
                game_state = gameState
            };

            var response = await PostAsync<StrategicPlanResponse>(
                "/strategic-plan", request);
            return response;
        }

        public async Task<string> StartRound(
            string gameId,
            int roundNumber,
            GameStateExport gameState)
        {
            var request = new
            {
                game_id = gameId,
                round_number = roundNumber,
                game_state = gameState
            };

            var response = await PostAsync<RoundStartResponse>(
                "/round/start", request);

            // Validate session_id was returned
            if (string.IsNullOrEmpty(response?.session_id))
            {
                Debug.LogError("StartRound response missing session_id");
                throw new InvalidOperationException("StartRound did not return a valid session_id");
            }

            _currentSessionId = response.session_id;
            return _currentSessionId;
        }

        public async Task<DecisionResponse> RequestDecision(
            DecisionType type,
            string shipId = null,
            string[] availableOptions = null,
            object context = null)
        {
            if (string.IsNullOrEmpty(_currentSessionId))
                throw new InvalidOperationException("No active round session");

            var request = new
            {
                game_id = "",  // Not needed, session has it
                session_id = _currentSessionId,
                decision_type = type.ToString().ToLower(),
                ship_id = shipId,
                available_options = availableOptions,
                context = context
            };

            return await PostAsync<DecisionResponse>("/decide", request);
        }

        public async Task UpdateRoundState(GameStateExport gameState, string eventDescription = null)
        {
            if (string.IsNullOrEmpty(_currentSessionId))
                return;

            var request = new
            {
                session_id = _currentSessionId,
                game_state = gameState,
                @event = eventDescription
            };

            await PostAsync<object>("/round/update", request);
        }

        public async Task<RoundEndResponse> EndRound(
            GameStateExport gameState,
            string[] events = null)
        {
            if (string.IsNullOrEmpty(_currentSessionId))
                throw new InvalidOperationException("No active round session");

            var request = new
            {
                session_id = _currentSessionId,
                game_state = gameState,
                events = events ?? new string[0]
            };

            var response = await PostAsync<RoundEndResponse>("/round/end", request);
            _currentSessionId = null;
            return response;
        }

        public async Task<bool> HealthCheck()
        {
            try
            {
                var response = await _client.GetAsync(_baseUrl + "/health");
                return response.IsSuccessStatusCode;
            }
            catch
            {
                return false;
            }
        }

        private async Task<T> PostAsync<T>(string endpoint, object data) where T : class
        {
            var json = JsonConvert.SerializeObject(data);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            try
            {
                var response = await _client.PostAsync(_baseUrl + endpoint, content);
                var responseBody = await response.Content.ReadAsStringAsync();

                if (!response.IsSuccessStatusCode)
                {
                    Debug.LogError($"AI Agent error: {response.StatusCode} - {responseBody}");
                    throw new HttpRequestException($"Request failed: {response.StatusCode}");
                }

                var result = JsonConvert.DeserializeObject<T>(responseBody);

                // Validate deserialization succeeded
                if (result == null)
                {
                    Debug.LogError($"AI Agent returned null after deserializing response from {endpoint}");
                    Debug.LogError($"Response body was: {responseBody?.Substring(0, Math.Min(500, responseBody?.Length ?? 0))}");
                    throw new InvalidOperationException($"Failed to deserialize response from {endpoint}");
                }

                return result;
            }
            catch (JsonException jsonEx)
            {
                Debug.LogError($"AI Agent JSON parsing error for {endpoint}: {jsonEx.Message}");
                throw;
            }
            catch (Exception ex)
            {
                Debug.LogError($"AI Agent communication error: {ex.Message}");
                throw;
            }
        }
    }

    public enum DecisionType
    {
        Planning,
        Action,
        Target,
        DiceMod
    }
}
