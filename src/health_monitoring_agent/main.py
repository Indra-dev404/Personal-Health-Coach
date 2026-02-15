"""
Main entry point for Health Monitoring Agent CLI.
"""

import sys
from .ui import HealthMonitoringUI
from .privacy import PrivacyModule


def main():
    """Run the Health Monitoring Agent CLI."""
    print("=" * 60)
    print("     Health Monitoring Agent")
    print("=" * 60)
    
    # For demo purposes, use a simple user setup
    # In production, would have proper user registration/login
    user_id = "demo_user"
    
    # Derive encryption key from password
    privacy_module = PrivacyModule()
    password = "demo_password"  # In production, would prompt securely
    user_key, _ = privacy_module.derive_key_from_password(password)
    
    # Initialize UI
    ui = HealthMonitoringUI(user_id, user_key)
    
    # Main menu loop
    while True:
        print("\n" + "=" * 60)
        print("Main Menu")
        print("=" * 60)
        print("1. Record Vital Signs")
        print("2. Record Activity")
        print("3. Record Symptom")
        print("4. View Recommendations")
        print("5. View Wellness Trends (7 days)")
        print("6. View Wellness Trends (30 days)")
        print("7. Exit")
        print()
        
        choice = input("Select an option (1-7): ").strip()
        
        if choice == "1":
            ui.input_vital_signs()
        elif choice == "2":
            ui.input_activity()
        elif choice == "3":
            ui.input_symptom()
        elif choice == "4":
            ui.view_recommendations()
        elif choice == "5":
            ui.view_wellness_trends(days=7)
        elif choice == "6":
            ui.view_wellness_trends(days=30)
        elif choice == "7":
            print("\nThank you for using Health Monitoring Agent!")
            sys.exit(0)
        else:
            print("\n✗ Invalid option. Please select 1-7.")


if __name__ == "__main__":
    main()
