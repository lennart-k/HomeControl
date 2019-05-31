API Module
==========

The HTTP API for HomeControl
Currenty it supports following routes:

.. http:get:: /api/ping

   Ping the API

   **Example request**:

   .. sourcecode:: http

      GET /api/ping HTTP/ HTTP/1.1
      Host: homecontrol.local:8080
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json; charset=utf-8

      {
         "data": "PONG",
         "status_code": 200,
         "success": true
      }

   :resheader Content-Type: application/json

   :statuscode 200: HomeControl is online
