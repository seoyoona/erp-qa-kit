# Pipe Manufacturing Demo Requirements

This generic demo ERP covers inventory, purchase, and production flows for pipe
manufacturing. It uses placeholder names only.

Core data-integrity concerns:

- Confirmed purchase receipts must affect inventory.
- Shipments must decrease stock and cancellations must restore stock.
- Production completion must record output and inventory movement.
- Purchase and production statuses must block invalid downstream actions.

