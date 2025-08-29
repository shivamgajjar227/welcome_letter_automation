class OrganizationNotFoundException(Exception):
    def __init__(self, message="❌ No organization data found"):
        super().__init__(message)