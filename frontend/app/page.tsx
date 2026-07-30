"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, RefreshCw, Plus, CheckCircle, AlertCircle, Plane } from "lucide-react";

import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/dashboard/Header";
import DashboardMetrics from "@/components/dashboard/DashboardMetrics";
import TripTabs from "@/components/dashboard/TripTabs";
import AddFlightCard from "@/components/dashboard/AddFlightCard";
import CreateTripModal from "@/components/dashboard/CreateTripModal";
import ConnectionCard from "@/components/dashboard/ConnectionCard";
import FlightStatusCard from "@/components/dashboard/FlightStatusCard";
import TripHero from "@/components/dashboard/TripHero";
import FlightTimeline from "@/components/dashboard/FlightTimeline";
import HotelCard from "@/components/dashboard/HotelCard";
import TransferCard from "@/components/dashboard/TransferCard";
import TripStatus from "@/components/dashboard/TripStatus";
import DataSourceBadge from "@/components/dashboard/DataSourceBadge";
import RefreshButton from "@/components/dashboard/RefreshButton";

import DisruptionAlert from "@/components/recovery/DisruptionAlert";
import RecoveryProgress from "@/components/recovery/RecoveryProgress";
import AlternativeFlights from "@/components/recovery/AlternativeFlights";
import SelectedFlight from "@/components/recovery/SelectedFlight";
import PolicyDecision from "@/components/recovery/PolicyDecision";
import RecoverySummary from "@/components/recovery/RecoverySummary";
import DecisionExplanation from "@/components/recovery/DecisionExplanation";

import {
  getTrip,
  getTrips,
  setupDemo,
  resetDemo,
  triggerDisruption,
  getProviderConfig,
  approveRecovery,
} from "@/lib/api";
import type {
  TripResponse,
  TripListItem,
  DisruptionResponse,
  ProviderConfig,
  TripMonitoringResponse,
  FlightSegment,
  Trip,
} from "@/types/reroute";

type AppState = "loading" | "healthy" | "disrupted" | "recovered";

const RECOVERY_STEPS = [
  { label: "Disruption detected", status: "complete" as const },
  { label: "Itinerary analyzed", status: "complete" as const },
  { label: "Missed connection identified", status: "complete" as const },
  { label: "Alternatives searched", status: "complete" as const },
  { label: "Best option selected", status: "complete" as const },
  { label: "Policy validated", status: "complete" as const },
  { label: "Flight rebooked", status: "complete" as const },
  { label: "Hotel updated", status: "complete" as const },
  { label: "Transfer rescheduled", status: "complete" as const },
  { label: "Traveler notified", status: "complete" as const },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [tripsList, setTripsList] = useState<TripListItem[]>([]);
  const [selectedTripId, setSelectedTripId] = useState<string>("TRIP001");
  const [tripData, setTripData] = useState<TripResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [appState, setAppState] = useState<AppState>("loading");
  const [disruptionData, setDisruptionData] = useState<DisruptionResponse | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [providerConfig, setProviderConfig] = useState<ProviderConfig | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Load all trips & selected trip data from backend
  const refreshAll = useCallback(async (tripIdToLoad?: string) => {
    const targetId = tripIdToLoad || selectedTripId;
    setLoading(true);
    try {
      // 1. Fetch trip list
      let listRes = await getTrips();
      if (!listRes.trips || listRes.trips.length === 0) {
        await setupDemo();
        listRes = await getTrips();
      }
      setTripsList(listRes.trips);

      // Determine valid target ID
      const validTripId = listRes.trips.some((t) => t.trip.trip_id === targetId)
        ? targetId
        : listRes.trips[0]?.trip.trip_id || "TRIP001";
      setSelectedTripId(validTripId);

      // 2. Fetch specific trip details
      const data = await getTrip(validTripId);
      setTripData(data);

      if (data.disruptions && data.disruptions.length > 0 && data.trip.status === "RECOVERY_REQUIRED") {
        setAppState("disrupted");
      } else if (data.trip.status === "RECOVERED") {
        setAppState("recovered");
      } else {
        setAppState("healthy");
      }
    } catch (err) {
      console.error("Failed to load trips:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedTripId]);

  useEffect(() => {
    refreshAll();
    getProviderConfig()
      .then(setProviderConfig)
      .catch(() => {/* ignore */});
  }, [refreshAll]);

  // 60-second automatic background trip polling
  useEffect(() => {
    const interval = setInterval(() => {
      if (selectedTripId && appState === "healthy") {
        refreshAll(selectedTripId);
      }
    }, 60000);
    return () => clearInterval(interval);
  }, [selectedTripId, appState, refreshAll]);

  const handleSelectTrip = (tripId: string) => {
    setSelectedTripId(tripId);
    refreshAll(tripId);
  };

  const handleReset = async () => {
    setIsSimulating(true);
    try {
      await resetDemo();
      await setupDemo();
      setDisruptionData(null);
      await refreshAll("TRIP001");
    } catch (error) {
      console.error("Reset failed:", error);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleDisruption = async () => {
    setIsSimulating(true);
    try {
      // Inject disruption into selected flight or default EK527
      const targetFlight = tripData?.flights[0]?.flight_number || "EK527";
      const data = await triggerDisruption(selectedTripId, targetFlight, 165);
      setDisruptionData(data);
      setAppState("disrupted");
      await refreshAll(selectedTripId);
    } catch (error) {
      console.error("Disruption failed:", error);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleApproveRecovery = async (approved: boolean) => {
    if (!disruptionData?.recovery_plan?.plan_id) return;
    try {
      await approveRecovery(disruptionData.recovery_plan.plan_id, approved);
      setAppState(approved ? "recovered" : "healthy");
      await refreshAll(selectedTripId);
    } catch (err) {
      console.error("Approval action failed:", err);
    }
  };

  const handleFlightAdded = async (newSegment: FlightSegment) => {
    await refreshAll(selectedTripId);
  };

  const handleTripCreated = async (newTrip: Trip) => {
    await refreshAll(newTrip.trip_id);
  };

  const activeDisruptionsCount = tripsList.filter(
    (t) => t.trip.status === "AT_RISK" || t.trip.status === "RECOVERY_REQUIRED"
  ).length;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        disruptionCount={activeDisruptionsCount}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header />

        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8 space-y-6 overflow-y-auto">
          {/* Provider status & Live Monitoring Bar */}
          <div className="flex flex-wrap items-center justify-between bg-zinc-900 border border-zinc-800 rounded-2xl px-5 py-3 gap-3 shadow-sm">
            <div className="flex items-center gap-3 text-sm">
              <span className="text-zinc-400 font-medium">Aviation Provider:</span>
              {providerConfig ? (
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white">{providerConfig.provider_name}</span>
                  {providerConfig.real_data_enabled ? (
                    <DataSourceBadge source="REAL" />
                  ) : (
                    <DataSourceBadge source="DEMO" />
                  )}
                </div>
              ) : (
                <DataSourceBadge source="DEMO" />
              )}
            </div>

            <div className="flex items-center gap-3">
              <RefreshButton
                tripId={selectedTripId}
                onRefreshed={() => refreshAll(selectedTripId)}
                cooldownSeconds={10}
              />
            </div>
          </div>

          <AnimatePresence mode="wait">
            {loading ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center justify-center py-20"
              >
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
              </motion.div>
            ) : (
              <motion.div
                key="content"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                className="space-y-6"
              >
                {/* 1. Dashboard Metrics Row */}
                <DashboardMetrics tripsList={tripsList} />

                {/* 2. Add New Flight to Monitor */}
                <AddFlightCard
                  tripId={selectedTripId}
                  onFlightAdded={handleFlightAdded}
                />

                {/* 3. My Trips Selector & Tabs */}
                <TripTabs
                  tripsList={tripsList}
                  selectedTripId={selectedTripId}
                  onSelectTrip={handleSelectTrip}
                  onCreateTripClick={() => setIsCreateModalOpen(true)}
                />

                {/* 4. Active Trip Recovery / Details Views */}
                {tripData && (
                  <>
                    {appState === "healthy" ? (
                      <div className="space-y-6">
                        <TripHero trip={tripData.trip} flights={tripData.flights} />

                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                          <div className="lg:col-span-2 space-y-6">
                            <FlightTimeline flights={tripData.flights} />
                          </div>
                          <div className="space-y-6">
                            <ConnectionCard segments={tripData.flights} />
                            <HotelCard hotel={tripData.hotel} />
                            <TransferCard transfer={tripData.transfer} />
                          </div>
                        </div>

                        <TripStatus tripData={tripData} loading={false} />

                        {/* Demo Controls */}
                        <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6 shadow-sm">
                          <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                            Demo & Disruption Testing Controls
                          </h3>
                          <p className="text-xs text-zinc-500 mb-4">
                            Simulates a disruption (+165 min delay) over your real/demo flight data.
                            Disruption is clearly labeled as simulated.
                          </p>
                          <div className="flex gap-3 flex-wrap">
                            <button
                              onClick={handleDisruption}
                              disabled={isSimulating}
                              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-xl disabled:opacity-50 transition-colors"
                            >
                              {isSimulating ? (
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                              ) : (
                                <Play className="w-4 h-4" />
                              )}
                              Simulate Disruption (+165 min)
                            </button>
                            <button
                              onClick={handleReset}
                              disabled={isSimulating}
                              className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold rounded-xl disabled:opacity-50 transition-colors"
                            >
                              <RefreshCw className="w-4 h-4" />
                              Reset Demo
                            </button>
                          </div>
                          <div className="mt-3 px-3 py-2 bg-amber-950/30 border border-amber-800/60 rounded-xl">
                            <p className="text-xs text-amber-400">
                              ⚠ <strong>Simulated disruption</strong> — Injects a +165 minute delay. Real itinerary data is displayed; disruption is artificial for demo testing.
                            </p>
                          </div>
                        </div>
                      </div>
                    ) : appState === "disrupted" && disruptionData ? (
                      <div className="space-y-6">
                        <DisruptionAlert
                          flight={disruptionData.disruption.flight}
                          delayMinutes={disruptionData.disruption.delay_minutes}
                          affectedFlight={disruptionData.impact_analysis.affected_flight}
                          connectionBuffer={disruptionData.impact_analysis.connection_buffer_minutes}
                        />

                        <RecoveryProgress steps={RECOVERY_STEPS} />

                        <AlternativeFlights
                          validOptions={disruptionData.alternatives.valid}
                          rejectedOptions={disruptionData.alternatives.rejected}
                        />

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          <SelectedFlight
                            option={{
                              ...disruptionData.decision,
                              flight_number: disruptionData.decision.selected_flight,
                              origin: disruptionData.alternatives.valid[0]?.origin || "",
                              destination: disruptionData.alternatives.valid[0]?.destination || "",
                              departure: disruptionData.alternatives.valid[0]?.departure || "",
                              arrival: disruptionData.alternatives.valid[0]?.arrival || "",
                              available_seats: 0,
                              cabin: "",
                              score_breakdown: { cost: 0, arrival: 0, airline: 0, cabin: 0, safety: 0 },
                              penalties: [],
                              connection_buffer_minutes: 0,
                              rank: 1,
                            }}
                            bookingReference={disruptionData.execution.booking_reference ?? undefined}
                          />
                          <PolicyDecision
                            decision={disruptionData.policy.decision}
                            reason={disruptionData.policy.reason}
                            option={{
                              ...disruptionData.decision,
                              flight_number: disruptionData.decision.selected_flight,
                              origin: "",
                              destination: "",
                              departure: "",
                              arrival: "",
                              available_seats: 0,
                              cabin: "",
                              score_breakdown: { cost: 0, arrival: 0, airline: 0, cabin: 0, safety: 0 },
                              penalties: [],
                              connection_buffer_minutes: 0,
                              rank: 1,
                            }}
                            autoLimit={15000}
                          />
                        </div>

                        {/* Booking simulation badge */}
                        {disruptionData.execution.booking_mode === "SIMULATED" && (
                          <div className="px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-xl text-xs text-zinc-400 text-center">
                            booking_mode: <strong>SIMULATED</strong> — No real ticket issued
                          </div>
                        )}

                        <DecisionExplanation
                          option={{
                            ...disruptionData.decision,
                            flight_number: disruptionData.decision.selected_flight,
                            origin: "",
                            destination: "",
                            departure: "",
                            arrival: "",
                            available_seats: 0,
                            cabin: "",
                            score_breakdown: { cost: 0, arrival: 0, airline: 0, cabin: 0, safety: 0 },
                            penalties: [],
                            connection_buffer_minutes: 0,
                            rank: 1,
                          }}
                        />

                        <RecoverySummary data={disruptionData} />

                        <div className="flex justify-center gap-4">
                          {disruptionData.policy.decision === "APPROVAL_REQUIRED" ? (
                            <>
                              <button
                                onClick={() => handleApproveRecovery(false)}
                                className="px-5 py-2.5 bg-red-950/60 border border-red-800 text-red-400 rounded-xl hover:bg-red-900 transition-colors text-xs font-semibold"
                              >
                                Reject Plan
                              </button>
                              <button
                                onClick={() => handleApproveRecovery(true)}
                                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl transition-colors text-xs font-semibold"
                              >
                                Approve Recovery Plan
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => setAppState("recovered")}
                              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors font-medium text-sm"
                            >
                              Continue to Recovered State
                            </button>
                          )}
                        </div>
                      </div>
                    ) : appState === "recovered" ? (
                      <div className="space-y-6">
                        <TripHero trip={tripData.trip} flights={tripData.flights} />
                        <FlightTimeline flights={tripData.flights} />
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          <HotelCard hotel={tripData.hotel} />
                          <TransferCard transfer={tripData.transfer} />
                        </div>
                        <TripStatus tripData={tripData} loading={false} />

                        <div className="bg-emerald-950/30 border border-emerald-800 rounded-2xl p-8 text-center space-y-4">
                          <h2 className="text-2xl font-bold text-emerald-300">Trip Recovered</h2>
                          <p className="text-xs text-emerald-400">
                            ReRoute automatically repaired your itinerary.
                          </p>
                          {tripData?.recovery_plans[0] && (
                            <div className="inline-flex items-center gap-6 bg-zinc-900/80 border border-emerald-900/60 rounded-xl p-4 text-left">
                              <div>
                                <p className="text-xs text-emerald-400">Selected Flight</p>
                                <p className="font-bold text-base text-white">
                                  {tripData.recovery_plans[0].selected_flight}
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-emerald-400">Additional Cost</p>
                                <p className="font-bold text-base text-white">
                                  ₹{tripData.recovery_plans[0].additional_cost.toLocaleString()}
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-emerald-400">Recovery Score</p>
                                <p className="font-bold text-base text-white">
                                  {tripData.recovery_plans[0].recovery_score}/100
                                </p>
                              </div>
                            </div>
                          )}

                          <p className="text-xs text-zinc-500">
                            Booking mode: <strong>SIMULATED</strong>
                          </p>
                        </div>

                        <div className="flex justify-center">
                          <button
                            onClick={handleReset}
                            disabled={isSimulating}
                            className="flex items-center gap-2 px-6 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold rounded-xl transition-colors"
                          >
                            <RefreshCw className="w-4 h-4" />
                            Reset Demo
                          </button>
                        </div>
                      </div>
                    ) : null}
                  </>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>

      {/* Modal for creating a new trip */}
      <CreateTripModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen}
        onTripCreated={handleTripCreated}
      />
    </div>
  );
}
