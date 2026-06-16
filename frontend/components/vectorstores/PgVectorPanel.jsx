// components/vectorstores/PgVectorPanel.jsx

'use client';

import { useEffect, useState } from 'react';
import { RefreshCw, Database } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { Badge } from '@/components/common/Badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { EmptyState } from '@/components/common/EmptyState';
import { StoreMetrics } from '@/components/vectorstores/StoreMetrics';
import { getPgVectorStatus, getVectorStoreCollections, rebuildVectorIndex } from '@/services/vectorstores';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { formatCompactNumber } from '@/lib/utils';

export function PgVectorPanel({ storeId }) {
  const [status, setStatus] = useState(null);
  const [collections, setCollections] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [rebuildingId, setRebuildingId] = useState(null);

  const fetchData = async () => {
    if (!storeId) return;
    setIsLoading(true);
    try {
      const [statusData, collectionsData] = await Promise.all([
        getPgVectorStatus(storeId),
        getVectorStoreCollections(storeId),
      ]);
      setStatus(statusData);
      setCollections(collectionsData?.items || []);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [storeId]);

  const handleRebuild = async (collectionName) => {
    setRebuildingId(collectionName);
    try {
      await rebuildVectorIndex(storeId, collectionName);
      toast.success(`Rebuilding index for ${collectionName}`);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setRebuildingId(null);
    }
  };

  if (!storeId) {
    return (
      <EmptyState
        icon={Database}
        title="No PGVector store connected"
        description="Connect a PostgreSQL instance with the pgvector extension to view its status."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <Badge variant={status?.healthy ? 'success' : 'destructive'}>
          {status?.healthy ? 'Healthy' : 'Unreachable'}
        </Badge>
        <Button variant="outline" size="sm" onClick={fetchData} isLoading={isLoading}>
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      <StoreMetrics metrics={status} isLoading={isLoading} />

      <Card>
        <CardHeader>
          <CardTitle>Tables</CardTitle>
          <CardDescription>ivfflat / hnsw indexes configured on vector columns</CardDescription>
        </CardHeader>
        <CardContent>
          {collections.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tables found</p>
          ) : (
            <div className="flex flex-col divide-y divide-border">
              {collections.map((collection) => (
                <div key={collection.name} className="flex items-center justify-between py-2.5">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-medium text-foreground">{collection.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatCompactNumber(collection.vector_count)} rows ·{' '}
                      {collection.dimension} dimensions
                    </span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    isLoading={rebuildingId === collection.name}
                    onClick={() => handleRebuild(collection.name)}
                  >
                    Rebuild
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
