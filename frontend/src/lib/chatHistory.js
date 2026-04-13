import { supabase } from "../utils/supabase";

function friendlySupabaseError(error) {
  const message = String(error?.message || error || "");
  if (message.includes("relation") && message.includes("does not exist")) {
    return new Error(
      "Chat history tables are not set up in Supabase yet. Run the SQL in supabase/chat_history.sql, then refresh the app."
    );
  }
  return error instanceof Error ? error : new Error(message || "Supabase request failed");
}

function mapMessage(row) {
  if (row.role === "user") {
    return {
      id: row.id,
      role: "user",
      text: row.content,
    };
  }

  const payload = row.payload || {};
  return {
    id: row.id,
    role: "assistant",
    summary: row.content,
    recommendations: payload.recommendations || [],
    notes: payload.notes || [],
    sources: payload.sources || [],
  };
}

export async function listChatSessions(userId) {
  const { data, error } = await supabase
    .from("chat_sessions")
    .select("id, title, program, course_filter, created_at, updated_at")
    .eq("user_id", userId)
    .order("updated_at", { ascending: false });

  if (error) {
    throw friendlySupabaseError(error);
  }

  return data || [];
}

export async function listChatMessages(sessionId) {
  const { data, error } = await supabase
    .from("chat_messages")
    .select("id, role, content, payload, created_at")
    .eq("session_id", sessionId)
    .order("created_at", { ascending: true });

  if (error) {
    throw friendlySupabaseError(error);
  }

  return (data || []).map(mapMessage);
}

export async function createChatSession({ userId, title, program, courseFilter }) {
  const { data, error } = await supabase
    .from("chat_sessions")
    .insert({
      user_id: userId,
      title,
      program,
      course_filter: courseFilter,
    })
    .select("id, title, program, course_filter, created_at, updated_at")
    .single();

  if (error) {
    throw friendlySupabaseError(error);
  }

  return data;
}

export async function updateChatSession({ sessionId, title, program, courseFilter }) {
  const payload = {
    updated_at: new Date().toISOString(),
  };
  if (typeof title === "string") {
    payload.title = title;
  }
  if (typeof program === "string") {
    payload.program = program;
  }
  if (typeof courseFilter === "string") {
    payload.course_filter = courseFilter;
  }

  const { data, error } = await supabase
    .from("chat_sessions")
    .update(payload)
    .eq("id", sessionId)
    .select("id, title, program, course_filter, created_at, updated_at")
    .single();

  if (error) {
    throw friendlySupabaseError(error);
  }

  return data;
}

export async function saveChatMessage({ sessionId, userId, role, content, payload = {} }) {
  const { data, error } = await supabase
    .from("chat_messages")
    .insert({
      session_id: sessionId,
      user_id: userId,
      role,
      content,
      payload,
    })
    .select("id, role, content, payload, created_at")
    .single();

  if (error) {
    throw friendlySupabaseError(error);
  }

  return mapMessage(data);
}

export async function deleteChatSession(sessionId) {
  const { error } = await supabase.from("chat_sessions").delete().eq("id", sessionId);

  if (error) {
    throw friendlySupabaseError(error);
  }
}
