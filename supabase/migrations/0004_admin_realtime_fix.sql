-- Realtime's postgres_changes RLS evaluation for the admin policies
-- (`for all using (public.is_admin())`) was silently dropping every event:
-- is_admin() queries `profiles`, which itself has RLS enabled, and that
-- nested RLS-on-RLS lookup doesn't resolve inside Realtime's evaluation
-- context the way it does for a normal PostgREST/RPC call. Marking the
-- function SECURITY DEFINER makes it run with the function owner's
-- privileges, bypassing profiles' RLS for this one internal lookup only —
-- the function still just returns a boolean derived from the caller's own
-- auth.uid(), so it leaks nothing extra.
alter function public.is_admin() security definer set search_path = public;
