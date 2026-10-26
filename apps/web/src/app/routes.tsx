import { useRoutes, type RouteObject } from "react-router-dom";

import { SermonPage } from "../features/sermon/SermonPage";
import { SermonList } from "../features/sermons/SermonList";
import { SettingsPage } from "../features/settings/SettingsPage";
import { Layout } from "./Layout";
import { LevelPlaceholder } from "./LevelPlaceholder";
import { Shell } from "./Shell";

export const routes: RouteObject[] = [
  {
    element: <Shell />,
    children: [
      {
        element: <Layout />,
        children: [
          { path: "/", element: <SermonList /> },
          { path: "/sermons/:id", element: <SermonPage /> },
          { path: "/cuts/:id", element: <LevelPlaceholder notFound="Corte não encontrado." /> },
        ],
      },
      { path: "/settings", element: <SettingsPage /> },
    ],
  },
];

export function AppRoutes() {
  return useRoutes(routes);
}
