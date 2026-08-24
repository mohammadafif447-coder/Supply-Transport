-- 0002_order_transition_function.sql
-- Menegakkan state machine status order (lihat docs/02-SRS.md §2.1) secara atomik
-- di level database: update orders + insert order_tracking_events + bebaskan/kunci
-- ketersediaan driver, semuanya dalam satu transaksi (row locked via FOR UPDATE).

create or replace function public.transition_order_status(
  p_order_id uuid,
  p_new_status order_status,
  p_actor_profile_id uuid,
  p_note text default null,
  p_lat double precision default null,
  p_lng double precision default null,
  p_driver_id uuid default null,
  p_vehicle_id uuid default null,
  p_cancelled_reason text default null
) returns orders
language plpgsql
security definer
set search_path = public
as $$
declare
  v_order orders;
  v_allowed boolean := false;
begin
  select * into v_order from orders where id = p_order_id for update;
  if not found then
    raise exception 'ORDER_NOT_FOUND' using errcode = 'P0002';
  end if;

  if v_order.status = 'pending' and p_new_status = 'assigned' then
    v_allowed := true;
  elsif v_order.status = 'assigned' and p_new_status = 'picked_up' then
    v_allowed := true;
  elsif v_order.status = 'picked_up' and p_new_status = 'in_transit' then
    v_allowed := true;
  elsif v_order.status = 'in_transit' and p_new_status = 'delivered' then
    v_allowed := true;
  elsif v_order.status in ('pending', 'assigned') and p_new_status = 'cancelled' then
    v_allowed := true;
  end if;

  if not v_allowed then
    raise exception 'INVALID_TRANSITION:%->%', v_order.status, p_new_status using errcode = 'P0001';
  end if;

  if p_new_status = 'assigned' and (p_driver_id is null or p_vehicle_id is null) then
    raise exception 'DRIVER_AND_VEHICLE_REQUIRED' using errcode = 'P0004';
  end if;

  if p_new_status = 'delivered' and v_order.pod_required and v_order.pod_photo_url is null then
    raise exception 'POD_REQUIRED' using errcode = 'P0003';
  end if;

  update orders
  set
    status = p_new_status,
    driver_id = coalesce(p_driver_id, driver_id),
    vehicle_id = coalesce(p_vehicle_id, vehicle_id),
    delivered_at = case when p_new_status = 'delivered' then now() else delivered_at end,
    cancelled_reason = case when p_new_status = 'cancelled' then p_cancelled_reason else cancelled_reason end
  where id = p_order_id
  returning * into v_order;

  insert into order_tracking_events (order_id, status, note, lat, lng, created_by_profile_id)
  values (p_order_id, p_new_status, p_note, p_lat, p_lng, p_actor_profile_id);

  if p_new_status = 'assigned' and v_order.driver_id is not null then
    update drivers set is_available = false where id = v_order.driver_id;
  elsif p_new_status in ('delivered', 'cancelled') and v_order.driver_id is not null then
    update drivers set is_available = true where id = v_order.driver_id;
  end if;

  return v_order;
end;
$$;
