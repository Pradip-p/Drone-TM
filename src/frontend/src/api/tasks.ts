/* eslint-disable import/prefer-default-export */
import { getIndividualTask, getTaskWaypoint } from '@Services/tasks';
import { useQuery, UseQueryOptions } from '@tanstack/react-query';

export const useGetTaskWaypointQuery = (
  projectId: string,
  taskId: string,
  queryOptions?: Partial<UseQueryOptions>,
) => {
  return useQuery({
    queryKey: ['task-waypoints'],
    enabled: !!(projectId && taskId),
    queryFn: () => getTaskWaypoint(projectId, taskId),
    select: (res: any) => res.data,
    ...queryOptions,
  });
};

export const useGetIndividualTaskQuery = (
  taskId: string,
  queryOptions?: Partial<UseQueryOptions>,
) => {
  return useQuery({
    queryKey: ['task-description'],
    enabled: !!taskId,
    queryFn: () => getIndividualTask(taskId),
    select: (res: any) => res.data,
    ...queryOptions,
  });
};