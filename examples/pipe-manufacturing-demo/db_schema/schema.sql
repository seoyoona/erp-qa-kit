CREATE TABLE tbl_inventory_balance (
  item_id TEXT NOT NULL,
  warehouse_id TEXT NOT NULL,
  on_hand_qty NUMERIC NOT NULL,
  PRIMARY KEY (item_id, warehouse_id)
);

CREATE TABLE tbl_inventory_movement (
  movement_id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL,
  warehouse_id TEXT NOT NULL,
  movement_type TEXT NOT NULL,
  ref_doc_type TEXT NOT NULL,
  ref_doc_id TEXT NOT NULL,
  quantity NUMERIC NOT NULL,
  movement_status TEXT NOT NULL
);

CREATE TABLE tbl_purchase_order (
  purchase_order_id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL,
  ordered_qty NUMERIC NOT NULL,
  received_qty NUMERIC NOT NULL,
  status TEXT NOT NULL
);

CREATE TABLE tbl_purchase_receipt (
  receipt_id TEXT PRIMARY KEY,
  purchase_order_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  receipt_qty NUMERIC NOT NULL,
  receipt_status TEXT NOT NULL
);

CREATE TABLE tbl_shipment (
  shipment_id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL,
  warehouse_id TEXT NOT NULL,
  shipped_qty NUMERIC NOT NULL,
  shipment_status TEXT NOT NULL
);

CREATE TABLE tbl_work_order (
  work_order_id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL,
  planned_qty NUMERIC NOT NULL,
  allow_over_output BOOLEAN NOT NULL,
  status TEXT NOT NULL
);

CREATE TABLE tbl_production_result (
  production_result_id TEXT PRIMARY KEY,
  work_order_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  total_output_qty NUMERIC NOT NULL,
  good_qty NUMERIC NOT NULL,
  defect_qty NUMERIC NOT NULL,
  result_status TEXT NOT NULL
);

