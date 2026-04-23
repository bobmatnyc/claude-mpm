#!/usr/bin/env python3
"""Test script to verify dashboard metrics and connection status."""

import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By


def test_dashboard_metrics():
    """Test the dashboard metrics display."""
    driver = webdriver.Chrome()

    try:
        print("Opening dashboard...")
        driver.get("http://localhost:8765")

        # Wait for the dashboard to load
        time.sleep(3)

        # Check connection status
        try:
            connection_status = driver.find_element(By.ID, "connection-status")
            status_text = connection_status.text
            status_class = connection_status.get_attribute("class")
            print("\n✓ Connection Status Element Found:")
            print(f"  Text: {status_text}")
            print(f"  Class: {status_class}")
        except NoSuchElementException:
            print("\n✗ Connection Status Element NOT Found")

        # Check header metrics
        metrics = {
            "total-events": "Total Events",
            "events-per-minute": "Events Per Minute",
            "unique-types": "Unique Types",
            "error-count": "Error Count",
            "debug-events-received": "Debug Events Received",
            "debug-events-rendered": "Debug Events Rendered",
        }

        print("\n📊 Header Metrics:")
        for element_id, label in metrics.items():
            try:
                element = driver.find_element(By.ID, element_id)
                value = element.text
                print(f"  {label}: {value}")
            except NoSuchElementException:
                print(f"  {label}: NOT FOUND")

        # Check sidebar stats
        print("\n📊 Sidebar Stats:")
        try:
            stat_values = driver.find_elements(By.CLASS_NAME, "stat-value")
            stat_labels = driver.find_elements(By.CLASS_NAME, "stat-label")
            for i in range(min(len(stat_values), len(stat_labels))):
                print(f"  {stat_labels[i].text}: {stat_values[i].text}")
        except Exception:
            print("  Could not find sidebar stats")

        # Execute JavaScript to check internal state
        print("\n🔧 JavaScript State Check:")

        # Check socket connection
        socket_state = driver.execute_script(
            """
            if (window.socketClient) {
                return {
                    isConnected: window.socketClient.isConnected,
                    isConnecting: window.socketClient.isConnecting,
                    eventsCount: window.socketClient.events ? window.socketClient.events.length : 0,
                    socket: window.socketClient.socket ? {
                        connected: window.socketClient.socket.connected,
                        id: window.socketClient.socket.id
                    } : null
                };
            }
            return null;
        """
        )

        if socket_state:
            print("  Socket Client State:")
            print(f"    isConnected: {socket_state['isConnected']}")
            print(f"    isConnecting: {socket_state['isConnecting']}")
            print(f"    Events Count: {socket_state['eventsCount']}")
            if socket_state["socket"]:
                print(f"    Socket Connected: {socket_state['socket']['connected']}")
                print(f"    Socket ID: {socket_state['socket']['id']}")
        else:
            print("  Socket Client NOT FOUND")

        # Check EventViewer state
        event_viewer_state = driver.execute_script(
            """
            if (window.eventViewer) {
                return {
                    eventsCount: window.eventViewer.events ? window.eventViewer.events.length : 0,
                    filteredEventsCount: window.eventViewer.filteredEvents ? window.eventViewer.filteredEvents.length : 0,
                    errorCount: window.eventViewer.errorCount,
                    eventsThisMinute: window.eventViewer.eventsThisMinute
                };
            }
            return null;
        """
        )

        if event_viewer_state:
            print("\n  Event Viewer State:")
            print(f"    Total Events: {event_viewer_state['eventsCount']}")
            print(f"    Filtered Events: {event_viewer_state['filteredEventsCount']}")
            print(f"    Error Count: {event_viewer_state['errorCount']}")
            print(f"    Events This Minute: {event_viewer_state['eventsThisMinute']}")
        else:
            print("\n  Event Viewer NOT FOUND")

        # Try to manually trigger metrics update
        print("\n🔄 Manually triggering metrics update...")
        update_result = driver.execute_script(
            """
            if (window.eventViewer && window.eventViewer.updateMetricsUI) {
                window.eventViewer.updateMetrics();
                window.eventViewer.updateMetricsUI();
                return {
                    success: true,
                    eventsCount: window.eventViewer.events.length,
                    metricsUpdated: true
                };
            }
            return { success: false, reason: 'EventViewer not found' };
        """
        )

        if update_result["success"]:
            print("  ✓ Metrics update triggered successfully")
            print(f"    Events Count: {update_result['eventsCount']}")

            # Check metrics again after update
            print("\n📊 Header Metrics After Update:")
            for element_id, label in metrics.items():
                try:
                    element = driver.find_element(By.ID, element_id)
                    value = element.text
                    print(f"  {label}: {value}")
                except NoSuchElementException:
                    print(f"  {label}: NOT FOUND")
        else:
            print(
                f"  ✗ Failed to trigger update: {update_result.get('reason', 'Unknown')}"
            )

        # Check for console errors
        console_logs = driver.get_log("browser")
        errors = [log for log in console_logs if log["level"] == "SEVERE"]
        if errors:
            print("\n⚠️ Console Errors Found:")
            for error in errors[:5]:  # Limit to first 5 errors
                print(f"  {error['message']}")
        else:
            print("\n✓ No console errors found")

        input("\nPress Enter to close the browser...")

    finally:
        driver.quit()


if __name__ == "__main__":
    test_dashboard_metrics()
