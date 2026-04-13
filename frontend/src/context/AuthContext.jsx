import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { supabase } from "../utils/supabase";

const AuthContext = createContext(undefined);

function mapSessionToUser(session) {
  if (!session?.user) {
    return null;
  }
  return {
    id: session.user.id || "",
    email: session.user.email || "",
    name:
      session.user.user_metadata?.full_name ||
      session.user.email?.split("@")[0] ||
      "UTA Student",
  };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;

    async function initializeAuth() {
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (session) {
          await supabase.auth.signOut();
        }

        if (!alive) {
          return;
        }
        setUser(null);
      } finally {
        if (alive) {
          setInitializing(false);
          setLoading(false);
        }
      }
    }

    initializeAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!alive) {
        return;
      }
      setUser(mapSessionToUser(session));
      setInitializing(false);
      setLoading(false);
    });

    return () => {
      alive = false;
      subscription.unsubscribe();
    };
  }, []);

  async function login(email, password) {
    setLoading(true);
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      return { error };
    } catch (error) {
      return { error };
    } finally {
      setLoading(false);
    }
  }

  async function signUp(email, password, name, program) {
    setLoading(true);
    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: name,
            program,
          },
        },
      });
      return { error };
    } catch (error) {
      return { error };
    } finally {
      setLoading(false);
    }
  }

  async function logout() {
    await supabase.auth.signOut();
    setUser(null);
  }

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      initializing,
      loading,
      login,
      signUp,
      logout,
    }),
    [user, initializing, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
