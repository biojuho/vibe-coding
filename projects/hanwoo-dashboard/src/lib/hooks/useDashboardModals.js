"use client";

import { useState, useCallback } from "react";

export function useDashboardModals() {
	const [showAddModal, setShowAddModal] = useState(false);
	const [quickActionIntent, setQuickActionIntent] = useState(null);
	const [selectedCow, setSelectedCow] = useState(null);
	const [isEditing, setIsEditing] = useState(false);
	const [deletingCattleId, setDeletingCattleId] = useState(null);
	const [selectedBuildingId, setSelectedBuildingId] = useState(null);
	const [selectedPenId, setSelectedPenId] = useState(null);
	const [showNotifications, setShowNotifications] = useState(false);

	const closeAddModal = useCallback(() => {
		setShowAddModal(false);
	}, []);

	const openAddModal = useCallback(() => {
		setShowAddModal(true);
	}, []);

	const closeNotifications = useCallback(() => {
		setShowNotifications(false);
	}, []);

	const openNotifications = useCallback(() => {
		setShowNotifications(true);
	}, []);

	const resetBuildingAndPen = useCallback(() => {
		setSelectedBuildingId(null);
		setSelectedPenId(null);
	}, []);

	return {
		showAddModal,
		setShowAddModal,
		quickActionIntent,
		setQuickActionIntent,
		selectedCow,
		setSelectedCow,
		isEditing,
		setIsEditing,
		deletingCattleId,
		setDeletingCattleId,
		selectedBuildingId,
		setSelectedBuildingId,
		selectedPenId,
		setSelectedPenId,
		showNotifications,
		setShowNotifications,
		closeAddModal,
		openAddModal,
		closeNotifications,
		openNotifications,
		resetBuildingAndPen,
	};
}
