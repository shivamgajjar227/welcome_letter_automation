

class NpiWlaTU:

    TU_TYPE_ID = 1
    """
    TODO Yash:
    - In any task unit class, first their states will be defined.
    - any state will be defined in the all caps.
    """
    TU_DATA_FETCHED_FROM_MONDAY = 1 # update this when all the required data will be updated in monday.
    TU_PROVIDER_PERSONAL_DETAILS_FETCHED = 2  # update this when Provider personal details fetched from Update menu
    TU_GROUP_DETAILS_FETCHED = 3  # update this when Provider Group details fetched from groups menu
    TU_GROUP_ADDRESS_FETCHED = 4 # update this when group address fetched from Practice menu
    TU_LOGGED_INTO_COMPANY = 5  # Logged into expected company of NPI on QC
    TU_NEW_NPI_QUICK_ADDED = 6  # update this when New NPI added through Quick Add
    TU_ERROR_ORG_ID_NOT_FOUND = 7 # update this when org id not found error occurs for provider
    TU_NPI_QUICK_ENTRY_DONE = 8  # update this when NPI quick entry completed
    TU_HEALTH_PLAN_ENTRY_DONE = 9  # update this when Health plan entry completed
    TU_OTHER_IDS_ENTRY_DONE = 10  # update this when Other IDs with taxonomy and provider ID entry completed
    TU_ANOTHER_NPI_ADDED = 11  # update this when Provider added successfully through Edit button
    TU_ANOTHER_HEALTH_PLAN_ADDED = 12  # update this when Health plan added for another NPI(this healthplan entry for which npi will added through edit button)
    TU_ANOTHER_OTHER_IDS_ADDED = 13  # update this when taxonomy and Other IDs added for another NPI(this taxonomy, provider id entry for which npi will added through edit button)
    TU_COMPANY_CHANGED = 14  # Company changed successfully based on NPI
    TU_COMPANY_CHANGE_NPI_QUICK_ADDED = 15  # After company change, NPI added through Quick Add
    TU_COMPANY_CHANGE_HEALTH_PLAN_ENTRY_DONE = 16  # After company change, health plan entry completed
    TU_COMPANY_CHANGE_OTHER_IDS_ADDED = 17  # After company change, taxonomy and other IDs added
    TU_COMPANY_CHANGE_ANOTHER_NPI_ADDED = 18  # After company change, another NPI added through Edit
    TU_COMPANY_CHANGE_ANOTHER_HEALTH_PLAN_ADDED = 19  # After company change, health plan added for another NPI
    TU_COMPANY_CHANGE_ANOTHER_OTHER_IDS_ADDED = 20  # After company change,taxonomy and other IDs for another NPI added
    TU_UPDATE_STATUS_ON_MONDAY = 21 # update this when successfully added npi on qc, mark as a review on monday or if data is not found(org data) mark as a roadblock



