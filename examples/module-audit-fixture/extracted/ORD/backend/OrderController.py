# erpqa:endpoint GET /api/orders OrderController.list
# erpqa:dto OrderListResponse order_no:string customer_code:string
# erpqa:procedure usp_order_list OrderRepository.findOrders
# erpqa:mapping order_no order_no OrderListResponse.order_no maps to grid column
# erpqa:mapping customer_code customer_code OrderListResponse.customer_code maps to grid column

def list_orders():
    return []
