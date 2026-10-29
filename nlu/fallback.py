class FallbackPolicy:
    DANGEROUS_TARGETS = {"shutdown", "restart", "sleep"}

    def is_dangerous(self, result):
        return (
            result.intent == "system"
            and (result.target_en or "") in self.DANGEROUS_TARGETS
        )