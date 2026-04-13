import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY;

const hasPlaceholderUrl =
  !supabaseUrl ||
  supabaseUrl.includes("your-project-id.supabase.co") ||
  supabaseUrl.includes("your-project-ref.supabase.co");
const hasPlaceholderKey =
  !supabaseKey ||
  supabaseKey.includes("your-supabase-anon-key") ||
  supabaseKey.includes("your-publishable-key");

if (hasPlaceholderUrl || hasPlaceholderKey) {
  throw new Error(
    "Supabase environment variables are missing or still using placeholder values. Set your real VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY in frontend/.env.local."
  );
}

export const supabase = createClient(supabaseUrl, supabaseKey);
