package com.example.integrationsuiteagent.tool;

import com.example.integrationsuiteagent.odata.ODataEntityTypeDto;
import com.example.integrationsuiteagent.odata.ODataMetadataDto;
import com.example.integrationsuiteagent.odata.ODataNavigationDto;
import com.example.integrationsuiteagent.odata.ODataPropertyDto;
import com.example.integrationsuiteagent.odata.ODataQueryCommand;
import com.example.integrationsuiteagent.odata.ODataQueryResult;
import com.example.integrationsuiteagent.odata.ODataServiceDto;
import dev.langchain4j.agent.tool.Tool;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

@Component
public class ODataDiscoveryTools {

    @Tool("List known OData services for a SAP system")
    public List<ODataServiceDto> listODataServices(String systemId) {
        return List.of(new ODataServiceDto(
                systemId,
                "API_PURCHASEORDER_2",
                "ODataV4",
                "SAP_COM_0053",
                "/sap/opu/odata4/sap/api_purchaseorder_2/srvd_a2x/sap/purchaseorder/0001/"
        ));
    }

    @Tool("Get OData metadata for a SAP service. Replace this stub with a real $metadata client.")
    public ODataMetadataDto getODataMetadata(String systemId, String serviceName) {
        if (!"API_PURCHASEORDER_2".equalsIgnoreCase(serviceName)) {
            return new ODataMetadataDto(systemId, serviceName, "UNKNOWN", List.of(), List.of());
        }
        ODataEntityTypeDto purchaseOrder = new ODataEntityTypeDto(
                serviceName,
                "PurchaseOrder",
                List.of("PurchaseOrder"),
                List.of(
                        new ODataPropertyDto("PurchaseOrder", "Edm.String", false, 10),
                        new ODataPropertyDto("CompanyCode", "Edm.String", true, 4),
                        new ODataPropertyDto("Supplier", "Edm.String", true, 10),
                        new ODataPropertyDto("PurchaseOrderType", "Edm.String", true, 4),
                        new ODataPropertyDto("DocumentCurrency", "Edm.String", true, 5)
                ),
                List.of(new ODataNavigationDto("_PurchaseOrderItem", "PurchaseOrderItem", true))
        );
        ODataEntityTypeDto item = new ODataEntityTypeDto(
                serviceName,
                "PurchaseOrderItem",
                List.of("PurchaseOrder", "PurchaseOrderItem"),
                List.of(
                        new ODataPropertyDto("PurchaseOrder", "Edm.String", false, 10),
                        new ODataPropertyDto("PurchaseOrderItem", "Edm.String", false, 5),
                        new ODataPropertyDto("Material", "Edm.String", true, 40),
                        new ODataPropertyDto("Plant", "Edm.String", true, 4),
                        new ODataPropertyDto("OrderQuantity", "Edm.Decimal", true, null)
                ),
                List.of()
        );
        return new ODataMetadataDto(systemId, serviceName, "ODataV4", List.of("PurchaseOrder", "PurchaseOrderItem"), List.of(purchaseOrder, item));
    }

    @Tool("Get entity type detail including keys, fields, and navigation properties")
    public ODataEntityTypeDto getEntityType(String systemId, String serviceName, String entityName) {
        return getODataMetadata(systemId, serviceName).entityTypes().stream()
                .filter(entityType -> entityType.entityName().equalsIgnoreCase(entityName))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Entity type not found: " + entityName));
    }

    @Tool("Run a sample OData query. Replace this stub with an authenticated SAP client.")
    public ODataQueryResult queryOData(ODataQueryCommand command) {
        String url = "/sap/opu/odata4/sap/api_purchaseorder_2/srvd_a2x/sap/purchaseorder/0001/"
                + command.entitySet()
                + "?$top=" + (command.top() == null ? 5 : command.top());
        return new ODataQueryResult(
                url,
                List.of(Map.of(
                        "PurchaseOrder", "4500000001",
                        "CompanyCode", "1000",
                        "Supplier", "1000001",
                        "DocumentCurrency", "CNY"
                )),
                "Stub result for agent planning. Configure a real SAP system client for live data."
        );
    }
}
