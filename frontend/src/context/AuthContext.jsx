import { createContext, useContext, useState } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem("maya_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const login = (userData, token) => {
    localStorage.setItem("maya_token", token);
    localStorage.setItem("maya_user", JSON.stringify(userData));
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem("maya_token");
    localStorage.removeItem("maya_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isAdmin: user?.role === "admin", login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
