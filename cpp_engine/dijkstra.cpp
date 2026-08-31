/**
 * Path Pilot - High-Performance C++ Dijkstra Engine
 * Phase 10: Standalone C++ Graph Engine utilizing Min-Heap Priority Queue,
 * Adjacency Lists, Distance Array, and Predecessor Tracking for Path Reconstruction.
 */

#include <iostream>
#include <vector>
#include <queue>
#include <string>
#include <sstream>
#include <limits>
#include <algorithm>
#include <cctype>

using namespace std;

const double INF = 1e18;

struct Edge {
    int to;
    double weight;
    string road_id;
};

struct EdgePredecessor {
    int from_node;
    string road_id;
};

// Fast and safe integer extraction from JSON fragment
int extract_int(const string& text, const string& key, int fallback = 0) {
    size_t pos = text.find("\"" + key + "\"");
    if (pos == string::npos) return fallback;
    size_t colon = text.find(':', pos + key.length() + 2);
    if (colon == string::npos) return fallback;
    
    size_t start = colon + 1;
    while (start < text.length() && (isspace(text[start]) || text[start] == '"')) {
        start++;
    }
    if (start >= text.length()) return fallback;

    size_t end = start;
    if (text[end] == '-') end++;
    while (end < text.length() && isdigit(text[end])) {
        end++;
    }
    if (start == end) return fallback;
    try {
        return stoi(text.substr(start, end - start));
    } catch (...) {
        return fallback;
    }
}

// Fast string extraction from JSON fragment
string extract_str(const string& text, const string& key) {
    size_t pos = text.find("\"" + key + "\"");
    if (pos == string::npos) return "";
    size_t colon = text.find(':', pos + key.length() + 2);
    if (colon == string::npos) return "";
    size_t q1 = text.find('"', colon);
    if (q1 == string::npos) return "";
    size_t q2 = text.find('"', q1 + 1);
    if (q2 == string::npos) return "";
    return text.substr(q1 + 1, q2 - q1 - 1);
}

// Fast double extraction from JSON fragment
double extract_double(const string& text, const string& key, double fallback = 1.0) {
    size_t pos = text.find("\"" + key + "\"");
    if (pos == string::npos) return fallback;
    size_t colon = text.find(':', pos + key.length() + 2);
    if (colon == string::npos) return fallback;
    
    size_t start = colon + 1;
    while (start < text.length() && (isspace(text[start]) || text[start] == '"')) {
        start++;
    }
    if (start >= text.length()) return fallback;

    size_t end = start;
    if (text[end] == '-' || text[end] == '+') end++;
    while (end < text.length() && (isdigit(text[end]) || text[end] == '.' || text[end] == 'e' || text[end] == 'E')) {
        end++;
    }
    if (start == end) return fallback;
    try {
        return stod(text.substr(start, end - start));
    } catch (...) {
        return fallback;
    }
}

int main(int argc, char* argv[]) {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string input_json, line;
    while (getline(cin, line)) {
        input_json += line + "\n";
    }

    if (input_json.empty()) {
        cout << "{\"status\":\"error\",\"message\":\"Empty JSON input\"}\n";
        return 1;
    }

    int num_nodes = extract_int(input_json, "num_nodes", 50);
    int source = extract_int(input_json, "source", 0);
    int destination = extract_int(input_json, "destination", 0);

    vector<vector<Edge>> adj(max(num_nodes + 20, 200));

    size_t edges_pos = input_json.find("\"edges\"");
    if (edges_pos != string::npos) {
        size_t cur = edges_pos;
        while ((cur = input_json.find('{', cur)) != string::npos) {
            size_t end_obj = input_json.find('}', cur);
            if (end_obj == string::npos) break;
            string edge_str = input_json.substr(cur, end_obj - cur + 1);
            
            int u = extract_int(edge_str, "from", -1);
            int v = extract_int(edge_str, "to", -1);
            double w = extract_double(edge_str, "weight", 1.0);
            string r_id = extract_str(edge_str, "road_id");

            if (u >= 0 && v >= 0) {
                if ((size_t)max(u, v) >= adj.size()) {
                    adj.resize(max(u, v) + 50);
                }
                // Weights must be non-negative for Dijkstra
                adj[u].push_back({v, max(0.001, w), r_id});
            }
            cur = end_obj + 1;
        }
    }

    int total_nodes = adj.size();
    if (source < 0 || source >= total_nodes || destination < 0 || destination >= total_nodes) {
        cout << "{\"status\":\"error\",\"message\":\"Node index out of bounds: source=" << source << ", dest=" << destination << "\"}\n";
        return 1;
    }

    // Dijkstra's Shortest Path Algorithm
    vector<double> dist(total_nodes, INF);
    vector<EdgePredecessor> parent(total_nodes, {-1, ""});
    // Min-Heap Priority Queue: (distance, node)
    priority_queue<pair<double, int>, vector<pair<double, int>>, greater<pair<double, int>>> pq;

    dist[source] = 0.0;
    pq.push({0.0, source});

    while (!pq.empty()) {
        auto top = pq.top();
        pq.pop();
        double d = top.first;
        int u = top.second;

        if (d > dist[u]) continue;
        if (u == destination) break;

        for (const auto& edge : adj[u]) {
            int v = edge.to;
            double weight = edge.weight;
            if (dist[u] + weight < dist[v]) {
                dist[v] = dist[u] + weight;
                parent[v] = {u, edge.road_id};
                pq.push({dist[v], v});
            }
        }
    }

    if (dist[destination] >= INF / 2.0) {
        cout << "{\n  \"status\": \"success\",\n  \"found\": false,\n  \"source\": " << source 
             << ",\n  \"destination\": " << destination << ",\n  \"total_cost\": -1.0,\n  \"node_path\": [],\n  \"edge_path\": []\n}\n";
        return 0;
    }

    // Path Reconstruction from destination back to source
    vector<int> node_path;
    vector<string> edge_path;
    int curr = destination;
    while (curr != source && curr != -1) {
        node_path.push_back(curr);
        edge_path.push_back(parent[curr].road_id);
        curr = parent[curr].from_node;
    }
    node_path.push_back(source);

    reverse(node_path.begin(), node_path.end());
    reverse(edge_path.begin(), edge_path.end());

    stringstream ss;
    ss << "{\n";
    ss << "  \"status\": \"success\",\n";
    ss << "  \"found\": true,\n";
    ss << "  \"source\": " << source << ",\n";
    ss << "  \"destination\": " << destination << ",\n";
    ss << "  \"total_cost\": " << dist[destination] << ",\n";
    ss << "  \"node_path\": [";
    for (size_t i = 0; i < node_path.size(); ++i) {
        ss << node_path[i] << (i + 1 < node_path.size() ? ", " : "");
    }
    ss << "],\n";
    ss << "  \"edge_path\": [";
    for (size_t i = 0; i < edge_path.size(); ++i) {
        ss << "\"" << edge_path[i] << "\"" << (i + 1 < edge_path.size() ? ", " : "");
    }
    ss << "]\n";
    ss << "}\n";

    cout << ss.str();
    return 0;
}
