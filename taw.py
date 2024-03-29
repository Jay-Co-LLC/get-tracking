import xml.etree.ElementTree as ET
import requests
import datetime
import config
import ordoro
import logging

url = config.taw_url

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
}

logger = logging.getLogger('get-tracking')


def __post_get_tracking(PONumber):
    return requests.post(
        f"{url}/GetTrackingInfo",
        data=f"UserID={__get_user()}&Password={__get_pass()}&PONumber={PONumber}&OrderNumber=",
        headers=headers)


def __get_user():
    return config.taw_username


def __get_pass():
    return config.taw_password


def get_tracking():
    logger.info("Requesting all TAW orders with 'Awaiting Tracking' from Ordoro...")
    robj = ordoro.get_await_track_orders(ordoro.supplier_taw_id)

    ord_orders = robj['order']

    logger.info(f"Found {len(ord_orders)} to process.")

    for eachOrder in ord_orders:
        # Determine if order should be skipped based on what mode we're in
        if config.should_skip(eachOrder['order_number']):
            logger.info(f"Skipping order {eachOrder['order_number']}.\n\r")
            continue

        PONumber = eachOrder['order_number']

        logger.info(f"Processing order {PONumber}...")
        logger.info("Requesting tracking info from TAW...")

        # ASK FOR TRACKING INFO FROM TAW
        try:
            r = __post_get_tracking(PONumber)
        except requests.exceptions.ConnectionError:
            logger.error("Unable to connect to TAW services. Skipping order.")
            continue

        logger.debug(f"Response from TAW:\n\r{r.content.decode('UTF-8')}")

        try:
            # PARSE TRACKING INFO FROM TAW RESPONSE
            root = ET.ElementTree(ET.fromstring(r.content)).getroot()

            records = root.findall('Record')
            if len(records) < 1:
                logger.info("No records received, skipping.\n\r")
                continue

            logger.info(f"{len(records)} records received, checking for tracking info...")

            i = 1
            for record in records:
                # For the first record, actually add the tracking number as shipping info
                if i == 1:
                    data = dict()

                    data['tracking_number'] = record.find('TrackNum').text.strip()

                    # IF NO TRACKING NUMBER, LOG IT AND GO ON TO THE NEXT ONE
                    if data['tracking_number'] == "":
                        logger.info("No tracking number found. Skipping.\n\r")
                        continue

                    order_date_str = record.find('OrderDate').text
                    order_date_obj = datetime.datetime.strptime(order_date_str, '%m/%d/%Y')
                    order_date_str = order_date_obj.strftime('%Y-%m-%dT%H:%M:%S.000Z')

                    data['ship_date'] = order_date_str
                    data['carrier_name'] = record.find('Type').text.strip()

                    # IF NO VENDOR, LOG IT AND GO ON TO THE NEXT ONE
                    if data['carrier_name'] == "":
                        logger.info("No vendor found. Skipping.\n\r")
                        continue

                    data['shipping_method'] = "ground"
                    data['cost'] = 14

                    logger.info(f"Applying {data['tracking_number']} as official shipping method...")
                    logger.debug(f"{data}")

                    # SEND TRACKING INFO TO ORDORO
                    r = ordoro.post_shipping_info(PONumber, data)

                    logger.info(f"Removing 'Awaiting Tracking' tag...")
                    ordoro.delete_tag_await_track(PONumber)
                else:
                    taw_invoice_num = record.find('InvoiceNumber').text.strip()
                    tracking_number = record.find('TrackNum').text.strip()

                    if tracking_number == "":
                        continue

                    logger.info(f"Applying {tracking_number} in a comment...")
                    ordoro.post_comment(
                        PONumber,
                        f'Additional tracking information: '
                        f'\n\rTAW Order ID: {taw_invoice_num}'
                        f'\n\rTracking Number: {tracking_number}')
                i = i + 1

        except Exception as err:
            logger.error(
                f"[{PONumber}] Error parsing tracking info..."
                f"\n\rException:"
                f"\n\r{err}"
                f"\n\rLast Response:"
                f"\n\r{r.content.decode('UTF-8')}")

        logger.info(f"Finished applying tracking for Ordoro order {PONumber}.\n\r")

    logger.info(f"Finished getting tracking info from TAW.\n\r")
