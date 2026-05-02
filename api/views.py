from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.serializers import RoutePlanSerializer
from services.routing_service import RoutingService
from services.fuel_optimizer import FuelOptimizer

_routing_service = RoutingService()
_fuel_optimizer = FuelOptimizer()


class RoutePlanView(APIView):
    def post(self, request):
        serializer = RoutePlanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        start = serializer.validated_data['start']
        finish = serializer.validated_data['finish']

        try:
            route = _routing_service.get_route(start, finish)
            result = _fuel_optimizer.optimize(route['coords'], route['distance_miles'])
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            'total_distance_miles': route['distance_miles'],
            'total_fuel_cost': result['total_fuel_cost'],
            'route_polyline': route['polyline'],
            'fuel_stops': result['fuel_stops'],
        })
