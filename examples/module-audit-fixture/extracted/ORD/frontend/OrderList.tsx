// erpqa:screen_id ORD_LIST
// erpqa:screen_name Order Lookup
// erpqa:route /orders OrderListComponent
// erpqa:api_call GET /api/orders
// erpqa:visible_text title_label|Order Lookup|1
// erpqa:search_filter order_date|Date|hidden
// erpqa:grid_column order_no|Order #|3
// erpqa:grid_column margin_rate|Margin Rate|2
// erpqa:form_field customer_code|Customer|readonly
// erpqa:button btn_search|Find|1
// erpqa:hidden internal_seq|Internal Sequence|visible

export function OrderListComponent() {
  return (
    <section>
      <h1>Order Lookup</h1>
      <button>Find</button>
    </section>
  );
}
