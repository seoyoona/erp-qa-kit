CREATE PROCEDURE usp_order_list
  @order_date date,
  @customer_code varchar(20)
AS
BEGIN
  SELECT order_no, customer_code
  FROM dbo.orders
  JOIN dbo.customers ON dbo.customers.customer_code = dbo.orders.customer_code;
END;
