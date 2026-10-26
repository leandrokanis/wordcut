import { useRoutes, type RouteObject } from "react-router-dom";

import { CutPage } from "../features/cut/CutPage";
import { SermonPage } from "../features/sermon/SermonPage";
import { SermonList } from "../features/sermons/SermonList";
import { SettingsPage } from "../features/settings/SettingsPage";
import { Layout } from "./Layout";
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
          { path: "/cuts/:id", element: <CutPage /> },
        ],
      },
      { path: "/settings", element: <SettingsPage /> },
    ],
  },
];

export function AppRoutes() {
  return useRoutes(routes);
}
