===============================
LovePop – Transfer Price Update
===============================

Daily updates products' Transfer Price from selected Pricelist
==============================================================

Added **Transfer Price Update** block to the *Pricing* settings in the *Sales* section of *Settings*

* If **Pricelist For Transfer Price Update** is selected there, a server action for Transfer Price update is created
* The server action runs :code:`transfer_price_update(company_id)` for the specified pricelist, which updates *Transfer Price* of *Products* set in the *Pricelist*'s lines:
    * For products that have valid lines (based on dates, min. quantity and compute price method), the most recent valid line is used to update the product's *Transfer Price*
    * For products with only lines that are expired or haven't started yet, product's *Transfer Price* is set to zero
    * All products affected have their *Transfer Price Currency* set to the pricelist's currency
    * The server action is first run on midnight (Indochina time) and repeats daily

Contributors:
=============

Lukáš Halda:
------------

* Created
