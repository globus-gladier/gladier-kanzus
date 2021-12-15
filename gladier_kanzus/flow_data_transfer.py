from gladier import GladierBaseClient, generate_flow_definition


@generate_flow_definition
class TransferFlow(GladierBaseClient):
    gladier_tools = [
        'gladier_kanzus.tools.TransferOut',
    ]

