const API_BASE = "/api/v1";

export const auth = {
  login: async (username, password) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) throw new Error("Login failed");
    return res.json();
  },

  register: async (username, password, email) => {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, email }),
    });
    if (!res.ok) throw new Error("Registration failed");
    return res.json();
  },

  me: async (token) => {
    const res = await fetch(`${API_BASE}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to fetch user");
    return res.json();
  },
};

export const learning = {
  getGoals: async (token) => {
    const res = await fetch(`${API_BASE}/goals`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to fetch goals");
    return res.json();
  },

  setGoals: async (token, goals) => {
    const res = await fetch(`${API_BASE}/goals`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ goals }),
    });
    if (!res.ok) throw new Error("Failed to set goals");
    return res.json();
  },

  generatePlan: async (token, topic, weeks, level) => {
    const res = await fetch(`${API_BASE}/plan/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ topic, weeks, level }),
    });
    if (!res.ok) throw new Error("Failed to generate plan");
    return res.json();
  },

  getRecommendations: async (token, query) => {
    const res = await fetch(`${API_BASE}/recommendations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) throw new Error("Failed to get recommendations");
    return res.json();
  },

  getPlans: async (token) => {
    const res = await fetch(`${API_BASE}/plans`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to fetch plans");
    return res.json();
  },
};
