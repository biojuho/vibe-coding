"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";
import { PremiumButton } from "@/components/ui/premium-button";

export class ErrorBoundary extends React.Component {
	constructor(props) {
		super(props);
		this.state = { hasError: false, error: null };
	}

	static getDerivedStateFromError(error) {
		return { hasError: true, error };
	}

	componentDidCatch(error, errorInfo) {
		console.error("[ErrorBoundary] Caught error:", error, errorInfo);
	}

	handleResetFailure = (resetError, message) => {
		console.error(message, resetError);
		this.setState({ hasError: true, error: resetError });
	};

	handleReset = () => {
		this.setState({ hasError: false, error: null });
		if (this.props.onReset) {
			try {
				const resetResult = this.props.onReset();
				if (resetResult && typeof resetResult.catch === "function") {
					resetResult.catch((resetError) => {
						this.handleResetFailure(
							resetError,
							"[ErrorBoundary] Failed to run reset handler:",
						);
					});
				}
			} catch (resetError) {
				this.handleResetFailure(
					resetError,
					"[ErrorBoundary] Failed to run reset handler:",
				);
			}
			return;
		}

		try {
			window.location.reload();
		} catch (resetError) {
			this.handleResetFailure(resetError, "[ErrorBoundary] Failed to reload:");
		}
	};

	render() {
		if (this.state.hasError) {
			if (this.props.fallback) {
				return this.props.fallback;
			}
			const resetButtonLabel = "대시보드 새로고침 및 복구 시도";
			return (
				<div role="alert" aria-live="assertive" className="flex flex-col items-center justify-center p-8 text-center min-h-[300px] border border-red-500/30 bg-red-950/20 rounded-xl">
					<AlertTriangle
						className="h-12 w-12 text-amber-500 mb-4 animate-pulse"
						aria-hidden="true"
					/>
					<h3 className="text-lg font-bold text-slate-100 mb-2">화면 표시 중 일시적인 오류가 발생했습니다.</h3>
					<p className="text-sm text-slate-400 max-w-md mb-6">
						화면 표시 정보가 올바르지 않거나 처리 중 예기치 못한 네트워크 문제가 발생했을 수 있습니다.
					</p>
					<PremiumButton
						type="button"
						onClick={this.handleReset}
						tone="primary"
						aria-label={resetButtonLabel}
						title={resetButtonLabel}
					>
						{resetButtonLabel}
					</PremiumButton>
				</div>
			);
		}

		return this.props.children;
	}
}

export default ErrorBoundary;
