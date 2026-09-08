-- ============================================================================
-- atelierR — order storage
--
-- Paste this whole file into the Supabase SQL Editor and press Run.
-- It is safe to run more than once.
--
-- The shape of the security here matters, because the key the website carries
-- is public by design. Anyone can therefore reach this database, so:
--
--   * the public may only INSERT — place an order, report a payment
--   * the public may never SELECT — nobody can read anyone's orders,
--     including their own; the customer's own copy stays in their browser
--   * only a signed-in atelierR account may read or change anything
--
-- Nothing here can mark an order paid. Payment is confirmed by a person.
-- ============================================================================

-- ---------------------------------------------------------------- orders ---
create table if not exists public.orders (
  id             uuid primary key default gen_random_uuid(),
  order_number   text unique not null,

  -- Frozen at the time of ordering: name, email, whatsapp, address,
  -- postal_code, notes. Kept as one document so a later change to the
  -- customer's details can never rewrite the history of a past order.
  customer       jsonb not null,

  -- Frozen line items: id, brand, name, shade, qty, unit_price, line_total.
  -- Prices are copied, not referenced, so repricing a product never alters
  -- what someone was charged.
  items          jsonb not null,

  subtotal       numeric(10,2) not null,
  delivery       numeric(10,2) not null,
  total          numeric(10,2) not null,
  currency       text not null default 'SGD',

  payment_method text not null default 'PayNow',
  -- unpaid → submitted (customer says they paid) → verified (atelierR checked)
  payment_status text not null default 'unpaid'
                 check (payment_status in ('unpaid', 'submitted', 'verified')),

  order_status   text not null default 'Order Created',
  status_key     text not null default 'CREATED'
                 check (status_key in ('CREATED', 'AWAITING_PAYMENT',
                                       'AWAITING_VERIFICATION', 'CONFIRMED',
                                       'PREPARING', 'SHIPPED', 'COMPLETED')),

  history        jsonb not null default '[]'::jsonb,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

create index if not exists orders_created_at_idx  on public.orders (created_at desc);
create index if not exists orders_status_key_idx  on public.orders (status_key);

-- ------------------------------------------------------- payment reports ---
-- A customer saying "I have paid" is a claim, not a fact, so it is recorded
-- separately rather than being allowed to touch the order row.
create table if not exists public.payment_reports (
  id           uuid primary key default gen_random_uuid(),
  order_number text not null,
  channel      text not null default 'upload' check (channel in ('upload', 'whatsapp')),
  screenshot   text,                    -- data URL, when the customer uploaded one
  note         text,
  created_at   timestamptz not null default now()
);

create index if not exists payment_reports_order_idx
  on public.payment_reports (order_number, created_at desc);

-- --------------------------------------------------- updated_at, honestly ---
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists orders_touch_updated_at on public.orders;
create trigger orders_touch_updated_at
  before update on public.orders
  for each row execute function public.touch_updated_at();

-- ------------------------------------------------------------------ RLS ----
alter table public.orders          enable row level security;
alter table public.payment_reports enable row level security;

-- The public may place an order and report a payment. Nothing else.
drop policy if exists "anyone may place an order" on public.orders;
create policy "anyone may place an order"
  on public.orders for insert to anon, authenticated
  with check (
    -- A new order always starts unpaid and unconfirmed, whatever the client
    -- sends. This is the guarantee that nothing can arrive pre-marked as paid.
    payment_status = 'unpaid'
    and status_key in ('CREATED', 'AWAITING_PAYMENT')
  );

drop policy if exists "anyone may report a payment" on public.payment_reports;
create policy "anyone may report a payment"
  on public.payment_reports for insert to anon, authenticated
  with check (true);

-- Only a signed-in atelierR account may read or change anything.
drop policy if exists "staff may read orders" on public.orders;
create policy "staff may read orders"
  on public.orders for select to authenticated using (true);

drop policy if exists "staff may update orders" on public.orders;
create policy "staff may update orders"
  on public.orders for update to authenticated using (true) with check (true);

drop policy if exists "staff may read payment reports" on public.payment_reports;
create policy "staff may read payment reports"
  on public.payment_reports for select to authenticated using (true);

-- Deliberately absent: any delete policy, and any select policy for anon.
-- Orders are never deleted, and the public can never read them back.

-- ---------------------------------------------------------------- grants ---
grant insert on public.orders          to anon, authenticated;
grant insert on public.payment_reports to anon, authenticated;
grant select, update on public.orders          to authenticated;
grant select          on public.payment_reports to authenticated;
