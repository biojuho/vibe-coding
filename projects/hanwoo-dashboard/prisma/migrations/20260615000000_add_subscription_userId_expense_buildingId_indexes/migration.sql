-- AddIndex: Subscription.userId+status
-- Hit on every AI/subscription API call for getSubscriptionStatus lookup
CREATE INDEX IF NOT EXISTS "Subscription_userId_status_idx" ON "Subscription"("userId", "status");

-- AddIndex: ExpenseRecord.buildingId+date
-- Covers per-barn expense aggregation queries
CREATE INDEX IF NOT EXISTS "ExpenseRecord_buildingId_date_idx" ON "ExpenseRecord"("buildingId", "date");
