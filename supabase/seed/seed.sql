-- Seed default commission_rules per tipe kendaraan.
-- Angka tarif (base_price, price_per_km) adalah PLACEHOLDER — sesuaikan dengan riset harga pasar sebelum go-live.

insert into commission_rules (vehicle_type, commission_percent, base_price, price_per_km) values
  ('motor',            15.00,  15000,  2000),
  ('pickup',           15.00,  75000,  4000),
  ('box_small',        15.00, 120000,  5500),
  ('box_medium',       15.00, 180000,  7000),
  ('truck_cdd',        12.00, 350000,  9000),
  ('truck_cdd_long',   12.00, 450000, 10500),
  ('truck_fuso',       10.00, 650000, 13000),
  ('truck_trailer',    10.00, 950000, 16000)
on conflict (vehicle_type) do nothing;
