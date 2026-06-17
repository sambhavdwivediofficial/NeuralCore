// app/monitoring/alerts.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Bell, Check, BellOff } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Badge } from '@/components/common/Badge';
import { EmptyState } from '@/components/common/EmptyState';
import { SkeletonText } from '@/components/common/Loader';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';
import { useAlerts } from '@/hooks/useMonitoring';
import { acknowledgeAlert, resolveAlert } from '@/services/monitoring';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';
import { ALERT_SEVERITY } from '@/lib/constants';
import { formatRelativeTime } from '@/lib/utils';

const SEVERITY_VARIANT = {
  [ALERT_SEVERITY.CRITICAL]: 'destructive',
  [ALERT_SEVERITY.WARNING]: 'warning',
  [ALERT_SEVERITY.INFO]: 'muted',
};

export default function MonitoringAlertsPage() {
  const router = useRouter();
  const [severity, setSeverity] = useState('all');
  const [status, setStatus] = useState('active');
  const { alerts, isLoading, refresh } = useAlerts({
    severity: severity === 'all' ? undefined : severity,
    status: status === 'all' ? undefined : status,
  });
  const [actioningId, setActioningId] = useState(null);

  const handleAcknowledge = async (alert) => {
    setActioningId(alert.id);
    try {
      await acknowledgeAlert(alert.id);
      toast.success('Alert acknowledged');
      refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setActioningId(null);
    }
  };

  const handleResolve = async (alert) => {
    setActioningId(alert.id);
    try {
      await resolveAlert(alert.id);
      toast.success('Alert resolved');
      refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setActioningId(null);
    }
  };

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <Button
          variant="ghost"
          size="sm"
          className="-ml-2 w-fit"
          onClick={() => router.push(ROUTES.MONITORING)}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Monitoring
        </Button>

        <div>
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Alerts</h1>
          <p className="text-sm text-muted-foreground">
            Active and historical alerts triggered by monitoring rules
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="acknowledged">Acknowledged</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
              <SelectItem value="all">All</SelectItem>
            </SelectContent>
          </Select>
          <Select value={severity} onValueChange={setSeverity}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              {Object.values(ALERT_SEVERITY).map((value) => (
                <SelectItem key={value} value={value} className="capitalize">
                  {value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {isLoading ? (
          <div className="card-surface p-4">
            <SkeletonText lines={6} />
          </div>
        ) : alerts.length === 0 ? (
          <EmptyState
            icon={Bell}
            title="No alerts"
            description="No alerts match the selected filters."
          />
        ) : (
          <div className="flex flex-col gap-2">
            {alerts.map((alert) => (
              <div key={alert.id} className="card-surface flex items-start justify-between gap-3 p-3">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <Badge variant={SEVERITY_VARIANT[alert.severity] || 'muted'}>{alert.severity}</Badge>
                    <span className="text-sm font-medium text-foreground">{alert.title}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{alert.description}</p>
                  <span className="text-2xs text-muted-foreground">
                    Triggered {formatRelativeTime(alert.triggered_at)}
                  </span>
                </div>

                {alert.status === 'resolved' ? (
                  <Badge variant="success">Resolved</Badge>
                ) : (
                  <div className="flex shrink-0 gap-2">
                    {alert.status !== 'acknowledged' ? (
                      <Button
                        variant="outline"
                        size="sm"
                        isLoading={actioningId === alert.id}
                        onClick={() => handleAcknowledge(alert)}
                      >
                        <Check className="h-3.5 w-3.5" />
                        Acknowledge
                      </Button>
                    ) : null}
                    <Button
                      variant="outline"
                      size="sm"
                      isLoading={actioningId === alert.id}
                      onClick={() => handleResolve(alert)}
                    >
                      <BellOff className="h-3.5 w-3.5" />
                      Resolve
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
