import requests
import config
import ordoro
import logging

logger = logging.getLogger('get-tracking')


def __get_url():
    return config.meyer_url


def __get_headers():
    return {
        'Authorization': config.meyer_auth,
        'Content-Type': 'application/json'
    }


def __get_sales_tracking(order_id):
    return requests.get(
        f"{__get_url()}/SalesTracking",
        params={'OrderNumber': order_id},
        headers=__get_headers()
    ).json()


def get_tracking():
    # Get all Awaiting Tracking orders associate with Meyer
    logger.info("Requesting all Meyer orders with 'Awaiting Tracking' from Ordoro...")
    rob = ordoro.get_await_track_orders(ordoro.supplier_meyer_id)

    if rob['count'] < 1:
        logger.info("No orders returned. Nothing to do.")
        return

    orders = rob['order']

    logger.info(f"Found {rob['count']} to process.")

    # Loop through orders
    for order in orders:
        # Determine if order should be skipped based on what mode we're in
        if config.should_skip(order['order_number']):
            logger.info(f"Skipping order {order['order_number']}.\n\r")
            continue

        logger.info(f"Processing order {order['order_number']}...")

        # Keep track of how many tracking numbers we get back, 1st is added as official shipping method
        num_tracking = 1
        for comment in order['comments']:
            if '[SR-MID]' in comment['text']:
                mey_order_id = comment['text'].split(':')[1].strip()

                logger.info(f"Asking Meyer for tracking info on order {mey_order_id}...")
                tracking_info = __get_sales_tracking(mey_order_id)

                # If what we get back isn't a list, it means nothing was found
                if not isinstance(tracking_info, list):
                    logger.info(f"Could not retrieve tracking info: {tracking_info['errorMessage']}, skipping.\n\r")
                    continue

                logger.info(f"Tracking info retrieved, processing...")

                for tracking in tracking_info:
                    # If this is the first tracking number, we add it as the official shipping method
                    if num_tracking == 1:
                        shipping_data = dict()

                        shipping_data['tracking_number'] = tracking['TrackingNumber']
                        shipping_data['ship_date'] = order['order_placed_date']
                        shipping_data['carrier_name'] = 'UPS'
                        shipping_data['shipping_method'] = 'ground'
                        shipping_data['cost'] = 13

                        logger.info(f"Applying {shipping_data['tracking_number']} as official shipping method...")
                        ordoro.post_shipping_info(order['order_number'], shipping_data)

                        logger.info("Removing 'Awaiting Tracking' tag...")
                        ordoro.delete_tag_await_track(order['order_number'])

                        num_tracking = num_tracking + 1
                    else:
                        # If this is not the first tracking number, add it as a comment
                        tracking_number = tracking['TrackingNumber']

                        logger.info(f"Applying {tracking_number} in a comment...")
                        ordoro.post_comment(
                            order['order_number'],
                            f"Additional tracking information: "
                            f"Order ID: {mey_order_id} "
                            f"Tracking Number: {tracking_number}"
                        )
                        num_tracking = num_tracking + 1

                logger.info(f"Finished applying tracking for Meyer order {mey_order_id}.")

        logger.info(f"Finished applying tracking for Ordoro order {order['order_number']}.\n\r")

    logger.info("Finished getting tracking info from Meyer.\n\r")