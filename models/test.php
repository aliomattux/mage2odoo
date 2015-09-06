<?php
    function multinfo($productIds, $includeLinks = false) {
	/* Fetch multiple products info */

	$store = null;
	$filters = null;
    $taxData = $this->getTaxInfo();
	$collection = Mage::getModel('catalog/product')
                ->getCollection()
                ->addAttributeToFilter('entity_id', array('in' => $productIds))
                ->addAttributeToSelect('*');

        $result = array ();

        foreach ($collection as $collection_item) {
            $coll_array = $collection_item->toArray();
            $coll_array['categories'] = $collection_item->getCategoryIds();
            $coll_array['websites'] = $collection_item->getWebsiteIds();
	        //If you want all kinds of links. Will make the call exponentially slower depending on number of links
	        if ($includeLinks) {
                if ($collection_item->getTypeId() == 'grouped') {
                    $coll_array['grouped'] = $this->getProductLinks($collection_item, Mage_Catalog_Model_Product_Link::LINK_TYPE_GROUPED);
                }
                $coll_array['up_sell'] = $this->getProductLinks($collection_item, Mage_Catalog_Model_Product_Link::LINK_TYPE_UPSELL);
                $coll_array['cross_sell'] = $this->getProductLinks($collection_item, Mage_Catalog_Model_Product_Link::LINK_TYPE_CROSSSELL);
                $coll_array['related'] = $this->getProductLinks($collection_item, Mage_Catalog_Model_Product_Link::LINK_TYPE_RELATED);
	        }

            /*TODO: Put this into a single function as its used more than once */
            if ($collection_item->getTypeId() == 'configurable') {
                $attribute_array = $collection_item->getTypeInstance(true)->getConfigurableAttributesAsArray($collection_item);
                $attrs = array();
                foreach ($attribute_array as $attr) {
                    $attrs[] = $attr['attribute_id'];

                }

                $coll_array['super_attributes'] = $attrs;
	        }

            $result[] = $coll_array;

        }

        return $result;
    }
